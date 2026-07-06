"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, Lock, CreditCard, Zap, Unlock, AlertTriangle, Loader, Star } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { tasksAPI, paymentsAPI } from "@/lib/api";
import { openRazorpayCheckout } from "@/lib/razorpay";

const STEPS = [
  { id: 0, icon: Lock,         label: "Lock Escrow",          desc: "Funds are held securely on the platform until work is verified." },
  { id: 1, icon: CreditCard,   label: "Pay via Razorpay",     desc: "Complete payment in the Razorpay checkout — your money stays protected." },
  { id: 2, icon: Zap,          label: "Task In Progress",      desc: "The tasker works while escrow stays locked." },
  { id: 3, icon: Unlock,       label: "Release Funds",         desc: "After verification, payment is released to the tasker." },
];

function PaymentsInner() {
  const { isLoggedIn, user } = useAuth();
  const searchParams = useSearchParams();
  const urlTaskId = searchParams?.get("task_id") || "";

  const [taskId, setTaskId] = useState(urlTaskId);
  const [currentStep, setCurrentStep] = useState(0);
  const [completing, setCompleting] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [ledger, setLedger] = useState([]);
  const [escrowData, setEscrowData] = useState(null);
  const [orderData, setOrderData] = useState(null);
  const [paymentData, setPaymentData] = useState(null);
  const [ratingScore, setRatingScore] = useState(5);
  const [ratingComment, setRatingComment] = useState("");
  const [ratingSubmitting, setRatingSubmitting] = useState(false);
  const [existingRating, setExistingRating] = useState(null);

  const isPoster = user?.role === "POSTER";

  // Auto-populate task ID from URL
  useEffect(() => {
    if (urlTaskId) setTaskId(urlTaskId);
  }, [urlTaskId]);

  useEffect(() => {
    if (!isLoggedIn || !taskId.trim() || currentStep < 4) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await tasksAPI.getMyRating(taskId.trim());
        if (!cancelled && data) setExistingRating(data);
      } catch (_) {
        if (!cancelled) setExistingRating(null);
      }
    })();
    return () => { cancelled = true; };
  }, [isLoggedIn, taskId, currentStep]);

  const addLedger = (label, detail, type = "info") => {
    setLedger((prev) => [
      ...prev,
      { id: Date.now() + Math.random(), label, detail, type, ts: new Date().toLocaleTimeString() },
    ]);
  };

  // ── Step 0: Lock Escrow ────────────────────────────────────────────────────
  const handleLockEscrow = async () => {
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    if (!taskId.trim()) { setApiError("Enter a Task ID first."); return; }
    setCompleting(true); setApiError(null);
    try {
      const data = await tasksAPI.startEscrow(taskId.trim());
      setEscrowData(data);
      addLedger("Escrow Locked", `Escrow ID: ${data.escrow_payment_id} · Amount: ₹${data.amount} ${data.currency} · Status: ${data.status}`, "success");
      setCurrentStep(1);
    } catch (err) {
      setApiError(err.message);
      addLedger("Escrow Lock Failed", err.message, "error");
    }
    setCompleting(false);
  };

  // ── Step 1: Create Razorpay order + open Checkout ─────────────────────────
  const handleCreateOrder = async () => {
    setCompleting(true); setApiError(null);
    try {
      const data = await paymentsAPI.createRazorpayOrder(taskId.trim());
      setOrderData(data);
      addLedger(
        "Razorpay Order Created",
        `Order ID: ${data.order_id} · Amount: ₹${data.amount} (${data.amount_paise} paise) · Escrow: ${data.escrow_id}`,
        "success"
      );

      let paid = false;
      const result = await openRazorpayCheckout(data, {
        taskId: taskId.trim(),
        onSuccess: (response) => {
          paid = true;
          setPaymentData(response);
          addLedger(
            "Checkout Payment Success",
            `payment_id: ${response.razorpay_payment_id} · order_id: ${response.razorpay_order_id}. Webhook will mark escrow captured.`,
            "success"
          );
          setCurrentStep(2);
        },
        onDismiss: () => {
          addLedger(
            "Checkout Closed",
            "Payment modal closed without completing. Order remains valid — retry Pay when ready.",
            "warn"
          );
        },
      });

      if (result.status === "dismissed" && !paid) {
        setApiError("Payment not completed. Click the step button again to reopen Checkout.");
      }
    } catch (err) {
      const isNotConfigured = err.message.includes("not configured") || err.message.includes("501");
      addLedger(
        isNotConfigured ? "Razorpay Not Configured" : "Payment Failed",
        isNotConfigured
          ? "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend .env to enable real payments."
          : err.message,
        isNotConfigured ? "warn" : "error"
      );
      if (isNotConfigured) {
        setCurrentStep(2);
      } else {
        setApiError(err.message);
      }
    }
    setCompleting(false);
  };

  // ── Step 2: Mark task in progress (UI only) ───────────────────────────────
  const handleInProgress = () => {
    addLedger("Task Started", "Tasker has started work. Escrow held securely.", "info");
    setCurrentStep(3);
  };

  // ── Step 3: Release Escrow ─────────────────────────────────────────────────
  const handleRelease = async () => {
    setCompleting(true); setApiError(null);
    try {
      const data = await tasksAPI.releaseEscrow(taskId.trim());
      addLedger(
        "Escrow Released ✓",
        `Status: ${data.status} · Payout: ${data.payout_status}`,
        "success"
      );
      setCurrentStep(4);
    } catch (err) {
      // If not RELEASE_ELIGIBLE, it might not yet be verified
      addLedger("Release Failed", `${err.message}. Run Verification first from the Verify page.`, "error");
      setApiError(err.message);
    }
    setCompleting(false);
  };

  const handleSubmitRating = async () => {
    if (!isLoggedIn || !isPoster) return;
    if (!taskId.trim()) { setApiError("Enter a Task ID first."); return; }
    setRatingSubmitting(true);
    setApiError(null);
    try {
      const data = await tasksAPI.rate(taskId.trim(), ratingScore, ratingComment.trim() || null);
      setExistingRating(data);
      addLedger("Tasker Rated", `Score: ${data.score}/5`, "success");
    } catch (err) {
      setApiError(err.message);
      addLedger("Rating Failed", err.message, "error");
    }
    setRatingSubmitting(false);
  };

  const stepHandlers = [handleLockEscrow, handleCreateOrder, handleInProgress, handleRelease];
  const stepBtnLabels = ["Lock escrow", "Pay with Razorpay", "Mark in progress", "Release funds"];

  const ledgerTypeColors = { info: "var(--color-text-muted)", success: "#10b981", error: "#f87171", warn: "#f59e0b" };

  return (
    <div className="payments-wrapper">
      <div className="pay-header-box">
        <h2 className="title-gradient-gold">Escrow Payment Flow</h2>
        <p>Secure Razorpay escrow — pay only when the job is done and verified.</p>
      </div>

      {!isLoggedIn && (
        <div className="pay-auth-warning">
          <AlertTriangle style={{ width: 16, height: 16 }} />
          <span>You must <a href="/login">sign in</a> as a Poster to manage escrow.</span>
        </div>
      )}

      {/* Task ID input */}
      <div className="task-id-input-row glass-card">
        <label>Task ID</label>
        <input
          type="text"
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
          placeholder="Enter Task UUID (auto-filled when coming from Tasker Radar)"
          className="task-id-input"
        />
        {taskId && (
          <span className="task-id-badge">
            Task: <code>{taskId.slice(0, 8)}...</code>
          </span>
        )}
      </div>

      {apiError && (
        <div className="api-error-bar">⚠ {apiError}</div>
      )}

      <div className="payments-layout">
        {/* Left: Step Machine */}
        <div className="steps-col">
          <div className="glass-card steps-card">
            <h3 className="steps-card-title">Escrow State Machine</h3>

            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isDone = idx < currentStep;
              const isActive = idx === currentStep && currentStep < 4;
              const isPending = idx > currentStep;

              return (
                <div key={step.id} className={`step-item ${isDone ? "step-done" : isActive ? "step-active" : "step-pending"}`}>
                  <div className="step-connector-col">
                    <div className={`step-circle ${isDone ? "circle-done" : isActive ? "circle-active" : "circle-pending"}`}>
                      {isDone ? (
                        <CheckCircle2 style={{ width: 18, height: 18 }} />
                      ) : (
                        <Icon style={{ width: 18, height: 18 }} />
                      )}
                    </div>
                    {idx < STEPS.length - 1 && (
                      <div className={`step-line ${isDone ? "line-done" : "line-pending"}`}></div>
                    )}
                  </div>

                  <div className="step-content">
                    <div className="step-content-header">
                      <h4>{step.label}</h4>
                      {isDone && <span className="done-badge">✓ Complete</span>}
                    </div>
                    <p className="step-desc">{step.desc}</p>

                    {isActive && (
                      <button
                        onClick={stepHandlers[idx]}
                        disabled={completing}
                        className="btn-premium btn-teal step-action-btn"
                      >
                        {completing ? (
                          <><Loader style={{ width: 14, height: 14, animation: "spin 1s linear infinite" }} /> Processing...</>
                        ) : (
                          stepBtnLabels[idx]
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {currentStep >= 4 && (
              <div className="completed-banner">
                <CheckCircle2 style={{ width: 28, height: 28, color: "#10b981" }} />
                <div>
                  <h4>Escrow Complete!</h4>
                  <p>Funds have been released to the tasker. The task lifecycle is complete.</p>
                </div>
              </div>
            )}

            {currentStep >= 4 && isPoster && (
              <div className="glass-card rating-card">
                <h4>Rate your tasker</h4>
                {existingRating ? (
                  <p className="rating-done">
                    You rated this task <strong>{existingRating.score}/5</strong>
                    {existingRating.comment ? ` — "${existingRating.comment}"` : ""}
                  </p>
                ) : (
                  <>
                    <div className="star-row">
                      {[1, 2, 3, 4, 5].map((n) => (
                        <button
                          key={n}
                          type="button"
                          className={`star-btn ${n <= ratingScore ? "active" : ""}`}
                          onClick={() => setRatingScore(n)}
                          aria-label={`Rate ${n} stars`}
                        >
                          <Star size={22} fill={n <= ratingScore ? "#f59e0b" : "none"} />
                        </button>
                      ))}
                    </div>
                    <textarea
                      rows={3}
                      placeholder="Optional comment about the work quality…"
                      value={ratingComment}
                      onChange={(e) => setRatingComment(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-premium btn-teal"
                      onClick={handleSubmitRating}
                      disabled={ratingSubmitting}
                    >
                      {ratingSubmitting ? "Submitting…" : "Submit rating"}
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Ledger + Info */}
        <div className="ledger-col">
          {/* Escrow summary */}
          {escrowData && (
            <div className="glass-card escrow-summary">
              <h4>Escrow Summary</h4>
              <div className="summary-grid">
                <div className="summary-cell"><span>Escrow ID</span><code>{escrowData.escrow_payment_id?.slice(0,8)}...</code></div>
                <div className="summary-cell"><span>Amount</span><strong>₹{escrowData.amount}</strong></div>
                <div className="summary-cell"><span>Currency</span><strong>{escrowData.currency}</strong></div>
                <div className="summary-cell"><span>Status</span><span className="escrow-status-chip">{escrowData.status}</span></div>
              </div>
              {orderData && (
                <div className="order-info">
                  <span>Razorpay Order ID:</span> <code>{orderData.order_id}</code>
                  {paymentData?.razorpay_payment_id && (
                    <div style={{ marginTop: 6 }}>
                      <span>Payment ID:</span> <code>{paymentData.razorpay_payment_id}</code>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Activity Ledger */}
          <div className="glass-card ledger-card">
            <h3 className="ledger-title">Activity Ledger</h3>
            {ledger.length === 0 ? (
              <p className="ledger-empty">No activity yet. Proceed through the escrow steps.</p>
            ) : (
              <div className="ledger-list">
                {ledger.map((entry) => (
                  <div key={entry.id} className="ledger-entry">
                    <div className="ledger-entry-header">
                      <span className="ledger-label" style={{ color: ledgerTypeColors[entry.type] }}>
                        {entry.label}
                      </span>
                      <span className="ledger-ts">{entry.ts}</span>
                    </div>
                    <p className="ledger-detail">{entry.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Info box */}
          <div className="glass-card info-card">
            <h4>About Razorpay Integration</h4>
            <ul>
              <li>Escrow is held on our platform and released only after verification passes.</li>
              <li>After escrow lock, <b>Razorpay Checkout</b> opens in a modal to collect payment.</li>
              <li>Requires <code>RAZORPAY_KEY_ID</code> &amp; <code>RAZORPAY_KEY_SECRET</code> in <code>backend_fastapi/.env</code>.</li>
              <li>Use Razorpay <b>test keys</b> in development; webhook confirms capture on the server.</li>
              <li>Payout to tasker uses <b>RazorpayX Payouts API</b> after escrow release.</li>
              <li>If verification fails, open a <a href={taskId ? `/disputes?task_id=${taskId}` : "/disputes"}>dispute</a> — admins resolve on the <a href="/admin">dashboard</a>.</li>
            </ul>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .payments-wrapper { display: flex; flex-direction: column; gap: 30px; }
        .pay-header-box { text-align: center; max-width: 600px; margin: 0 auto; display: flex; flex-direction: column; gap: 8px; }
        .title-gradient-gold { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .pay-auth-warning { display: flex; align-items: center; gap: 8px; justify-content: center; background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2); border-radius: 10px; padding: 12px 20px; color: var(--color-saffron); font-size: 0.85rem; font-weight: 600; }
        .pay-auth-warning a { color: var(--color-teal); text-decoration: underline; }
        .task-id-input-row { padding: 16px 20px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
        .task-id-input-row label { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); white-space: nowrap; }
        .task-id-input { flex: 1; min-width: 200px; background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px; padding: 10px 14px; color: var(--color-text-main); font-family: monospace; font-size: 0.85rem; outline: none; }
        .task-id-input:focus { border-color: var(--color-teal); }
        .task-id-badge { font-size: 0.78rem; color: var(--color-text-muted); white-space: nowrap; } .task-id-badge code { color: var(--color-teal); }
        .api-error-bar { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 0.85rem; }
        .payments-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; align-items: start; }
        .steps-card { padding: 28px; display: flex; flex-direction: column; gap: 0; }
        .steps-card-title { font-size: 1.2rem; font-weight: 700; margin-bottom: 28px; border-left: 3px solid var(--color-saffron); padding-left: 12px; }
        .step-item { display: flex; gap: 0; }
        .step-connector-col { display: flex; flex-direction: column; align-items: center; margin-right: 16px; }
        .step-circle { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border-width: 2px; border-style: solid; }
        .circle-done { background: rgba(16,185,129,0.1); border-color: #10b981; color: #10b981; }
        .circle-active { background: rgba(245,158,11,0.1); border-color: var(--color-saffron); color: var(--color-saffron); box-shadow: 0 0 14px rgba(245,158,11,0.3); }
        .circle-pending { background: rgba(255,255,255,0.03); border-color: var(--border-glow); color: var(--color-text-muted); }
        .step-line { width: 2px; flex: 1; min-height: 24px; margin: 4px 0; }
        .line-done { background: #10b981; }
        .line-pending { background: var(--border-glow); }
        .step-content { padding-bottom: 24px; flex: 1; }
        .step-content-header { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
        .step-content h4 { font-size: 1rem; font-weight: 700; }
        .step-done h4 { color: var(--color-text-muted); }
        .step-active h4 { color: var(--color-text-main); }
        .step-pending h4 { color: var(--color-text-muted); opacity: 0.5; }
        .done-badge { font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #10b981; font-weight: 700; }
        .step-desc { font-size: 0.78rem; color: var(--color-text-muted); margin-bottom: 10px; font-family: monospace; line-height: 1.4; }
        .step-action-btn { display: flex; align-items: center; gap: 8px; padding: 10px 18px; font-size: 0.9rem; }
        .completed-banner { display: flex; align-items: center; gap: 16px; padding: 20px; background: rgba(16,185,129,0.05); border: 1px solid rgba(16,185,129,0.2); border-radius: 12px; }
        .completed-banner h4 { font-size: 1rem; font-weight: 700; color: #10b981; }
        .completed-banner p { font-size: 0.85rem; color: var(--color-text-muted); }
        .rating-card { margin-top: 16px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
        .rating-card h4 { font-size: 1rem; font-weight: 700; }
        .rating-done { font-size: 0.85rem; color: var(--color-text-muted); }
        .star-row { display: flex; gap: 6px; }
        .star-btn { background: transparent; border: none; cursor: pointer; padding: 0; color: #64748b; }
        .star-btn.active { color: #f59e0b; }
        .rating-card textarea { background: rgba(7,9,19,0.5); border: 1px solid var(--border-glow); border-radius: 8px; padding: 10px 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.85rem; resize: vertical; }
        .ledger-col { display: flex; flex-direction: column; gap: 20px; }
        .escrow-summary { padding: 20px; }
        .escrow-summary h4 { font-size: 0.85rem; font-weight: 700; color: var(--color-teal); margin-bottom: 14px; text-transform: uppercase; }
        .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .summary-cell { display: flex; flex-direction: column; gap: 4px; }
        .summary-cell span { font-size: 0.72rem; color: var(--color-text-muted); font-weight: 600; }
        .summary-cell strong { font-size: 1rem; font-weight: 700; }
        .summary-cell code { font-size: 0.75rem; color: var(--color-teal); }
        .escrow-status-chip { font-size: 0.75rem; font-weight: 700; padding: 3px 8px; border-radius: 8px; background: rgba(20,184,166,0.1); color: var(--color-teal); border: 1px solid var(--border-teal); display: inline-block; }
        .order-info { margin-top: 12px; font-size: 0.8rem; color: var(--color-text-muted); border-top: 1px solid var(--border-glow); padding-top: 10px; }
        .order-info code { color: var(--color-teal); }
        .ledger-card { padding: 24px; }
        .ledger-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; }
        .ledger-empty { font-size: 0.85rem; color: var(--color-text-muted); }
        .ledger-list { display: flex; flex-direction: column; gap: 12px; max-height: 300px; overflow-y: auto; }
        .ledger-entry { padding: 12px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-glow); border-radius: 8px; display: flex; flex-direction: column; gap: 4px; }
        .ledger-entry-header { display: flex; justify-content: space-between; align-items: center; }
        .ledger-label { font-size: 0.8rem; font-weight: 700; }
        .ledger-ts { font-size: 0.7rem; color: var(--color-text-muted); }
        .ledger-detail { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.4; word-break: break-all; }
        .info-card { padding: 22px; }
        .info-card h4 { font-size: 0.9rem; font-weight: 700; color: var(--color-saffron); margin-bottom: 12px; }
        .info-card ul { display: flex; flex-direction: column; gap: 8px; padding-left: 16px; }
        .info-card li { font-size: 0.8rem; color: var(--color-text-muted); line-height: 1.4; }
        .info-card code { background: rgba(255,255,255,0.05); padding: 1px 4px; border-radius: 3px; font-size: 0.7rem; }
        @media (max-width: 900px) { .payments-layout { grid-template-columns: 1fr; } }
      ` }} />
    </div>
  );
}

export default function PaymentsPage() {
  return (
    <Suspense fallback={
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "50vh", color: "var(--color-text-muted)", gap: 12 }}>
        <Loader style={{ width: 24, height: 24, animation: "spin 1s linear infinite" }} />
        Loading Payments...
      </div>
    }>
      <PaymentsInner />
    </Suspense>
  );
}

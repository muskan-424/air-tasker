"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Loader2,
  MapPin,
  ShieldCheck,
  Star,
  Timer,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { tasksAPI } from "@/lib/api";
import TaskThreadChat from "@/components/TaskThreadChat";

const STEPS = [
  { key: "PUBLISHED", label: "Posted" },
  { key: "ACCEPTED", label: "Accepted" },
  { key: "IN_PROGRESS", label: "In progress" },
  { key: "COMPLETED", label: "Completed" },
];

function stepIndex(status) {
  const order = ["PUBLISHED", "ACCEPTED", "IN_PROGRESS", "COMPLETED"];
  const idx = order.indexOf(status);
  return idx >= 0 ? idx : 0;
}

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params?.id;
  const { isLoggedIn, user } = useAuth();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accepting, setAccepting] = useState(false);
  const [scopePrice, setScopePrice] = useState("");
  const [scopeNote, setScopeNote] = useState("");
  const [scopeBusy, setScopeBusy] = useState(false);

  const loadTask = useCallback(async () => {
    if (!taskId || !isLoggedIn) return;
    setLoading(true);
    setError(null);
    try {
      const data = await tasksAPI.get(taskId);
      setTask(data);
      const schema = data.task_schema || {};
      const range = schema.suggested_price_range || {};
      const defaultPrice = data.scope?.agreed_price || range.max || range.min || "";
      setScopePrice(defaultPrice ? String(defaultPrice) : "");
    } catch (err) {
      setError(err.message);
      setTask(null);
    } finally {
      setLoading(false);
    }
  }, [taskId, isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) {
      setLoading(false);
      return;
    }
    loadTask();
  }, [loadTask, isLoggedIn]);

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await tasksAPI.accept(taskId);
      await loadTask();
    } catch (err) {
      alert(`Accept failed: ${err.message}`);
    } finally {
      setAccepting(false);
    }
  };

  const handleProposeScope = async () => {
    const price = parseFloat(scopePrice);
    if (!price || price <= 0) {
      alert("Enter a valid price in INR");
      return;
    }
    setScopeBusy(true);
    try {
      await tasksAPI.proposeScope(taskId, {
        agreed_price: price,
        note: scopeNote || null,
        scope_json: { checklist: task?.task_schema?.completion_criteria || null },
      });
      await loadTask();
    } catch (err) {
      alert(err.message);
    } finally {
      setScopeBusy(false);
    }
  };

  const handleAcceptScope = async () => {
    setScopeBusy(true);
    try {
      await tasksAPI.acceptScope(taskId);
      await loadTask();
    } catch (err) {
      alert(err.message);
    } finally {
      setScopeBusy(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card page-card">
          <p>Please <Link href="/login">sign in</Link> to view this task.</p>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="page-shell">
        <div className="empty-state"><Loader2 className="spin-icon" size={24} /> Loading task...</div>
      </main>
    );
  }

  if (error || !task) {
    return (
      <main className="page-shell">
        <Link href="/my-tasks" className="back-link"><ArrowLeft size={16} /> Back to My Tasks</Link>
        <div className="error-banner">{error || "Task not found."}</div>
      </main>
    );
  }

  const schema = task.task_schema || {};
  const price = schema.suggested_price_range || {};
  const isTasker = user?.role === "TASKER";
  const isPoster = user?.id === task.poster_id;
  const isAssignedTasker = task.tasker_id && user?.id === task.tasker_id;
  const canAccept = isTasker && task.status === "PUBLISHED";
  const chatEnabled = task.status !== "PUBLISHED" && (isPoster || isAssignedTasker);
  const currentStep = stepIndex(task.status);
  const scope = task.scope;
  const scopeAccepted = scope?.status === "ACCEPTED";
  const scopePending = scope?.status === "PROPOSED";

  return (
    <main className="page-shell">
      <Link href={isTasker ? "/tasker" : "/my-tasks"} className="back-link">
        <ArrowLeft size={16} /> Back
      </Link>

      <div className="glass-card detail-card">
        <div className="detail-top">
          <span className="cat-chip">{task.category || "General"}</span>
          <span className="status-chip">{task.status.replace("_", " ")}</span>
        </div>

        <h1>{schema.title || task.subcategory || "Task"}</h1>
        <p className="desc">{schema.description || "No description provided."}</p>

        <div className="timeline">
          {STEPS.map((step, idx) => (
            <div key={step.key} className={`tl-step ${idx <= currentStep ? "done" : ""} ${idx === currentStep ? "active" : ""}`}>
              <div className="tl-dot" />
              <span>{step.label}</span>
            </div>
          ))}
        </div>

        <div className="meta-grid">
          <div><MapPin size={16} /> {schema.location || schema.location_pin || "India"}</div>
          <div><Timer size={16} /> {schema.estimated_duration_minutes || 60} min</div>
          {price.min != null && (
            <div><CreditCard size={16} /> ₹{price.min}–₹{price.max || price.min} suggested</div>
          )}
          {scopeAccepted && (
            <div><CheckCircle2 size={16} /> Agreed ₹{scope.agreed_price}</div>
          )}
          {task.escrow_status && (
            <div><ShieldCheck size={16} /> Escrow: {task.escrow_status}</div>
          )}
        </div>

        {schema.completion_criteria && (
          <section className="section">
            <h3>Completion criteria</h3>
            <p>{schema.completion_criteria}</p>
          </section>
        )}

        {task.status !== "PUBLISHED" && (
          <section className="section scope-section">
            <h3>Price agreement</h3>
            {scopeAccepted ? (
              <p className="scope-ok">Agreed price: <strong>₹{scope.agreed_price}</strong></p>
            ) : scopePending && isPoster ? (
              <div className="scope-pending">
                <p>Tasker proposed <strong>₹{scope.agreed_price}</strong>{scope.note ? ` — ${scope.note}` : ""}</p>
                <button type="button" className="btn-premium btn-teal" onClick={handleAcceptScope} disabled={scopeBusy}>
                  Accept price
                </button>
              </div>
            ) : scopePending ? (
              <p className="muted">Waiting for poster to accept ₹{scope.agreed_price}</p>
            ) : isAssignedTasker ? (
              <div className="scope-form">
                <label>
                  Your price (INR)
                  <input type="number" value={scopePrice} onChange={(e) => setScopePrice(e.target.value)} min="1" />
                </label>
                <label>
                  Note (optional)
                  <input type="text" value={scopeNote} onChange={(e) => setScopeNote(e.target.value)} placeholder="e.g. includes parts" />
                </label>
                <button type="button" className="btn-premium btn-saffron" onClick={handleProposeScope} disabled={scopeBusy}>
                  Propose price
                </button>
              </div>
            ) : (
              <p className="muted">Tasker will propose a final price after accepting.</p>
            )}
          </section>
        )}

        <div className="actions">
          {canAccept && (
            <button type="button" className="btn-premium btn-saffron" onClick={handleAccept} disabled={accepting}>
              {accepting ? "Accepting..." : "Accept task"}
            </button>
          )}
          {(isPoster || isAssignedTasker) && task.status !== "PUBLISHED" && (
            <>
              <Link href={`/verify?task_id=${task.id}`} className="btn-premium btn-teal action-link">
                <ShieldCheck size={16} /> Upload proof
              </Link>
              <Link href={`/payments?task_id=${task.id}`} className="btn-premium btn-teal action-link">
                <CreditCard size={16} /> Payments
              </Link>
              {task.status === "COMPLETED" && (
                <Link href={`/payments?task_id=${task.id}#rate`} className="btn-premium btn-outline action-link">
                  <Star size={16} /> Rate
                </Link>
              )}
            </>
          )}
        </div>
      </div>

      <TaskThreadChat taskId={taskId} userId={user?.id} enabled={chatEnabled} />

      <style jsx>{`
        .page-shell { max-width: 760px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .back-link { display: inline-flex; align-items: center; gap: 6px; color: var(--color-text-muted); text-decoration: none; font-size: 0.9rem; }
        .back-link:hover { color: var(--color-teal); }
        .detail-card { padding: 28px; display: flex; flex-direction: column; gap: 16px; }
        .detail-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
        .cat-chip { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--color-teal); }
        .status-chip { font-size: 0.72rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border-teal); color: var(--color-teal); text-transform: capitalize; }
        h1 { font-size: 1.8rem; font-weight: 800; }
        .desc { color: var(--color-text-muted); line-height: 1.6; }
        .timeline { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 0; }
        .tl-step { display: flex; align-items: center; gap: 6px; font-size: 0.75rem; color: var(--color-text-muted); }
        .tl-step.done { color: var(--color-teal); }
        .tl-step.active { font-weight: 700; }
        .tl-dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.15); }
        .tl-step.done .tl-dot { background: var(--color-teal); }
        .meta-grid { display: flex; flex-wrap: wrap; gap: 16px; color: var(--color-text-muted); font-size: 0.88rem; }
        .meta-grid div { display: flex; align-items: center; gap: 6px; }
        .section h3 { font-size: 0.95rem; margin-bottom: 6px; }
        .section p { color: var(--color-text-muted); font-size: 0.88rem; line-height: 1.5; }
        .scope-form { display: flex; flex-direction: column; gap: 10px; max-width: 360px; }
        .scope-form label { display: flex; flex-direction: column; gap: 4px; font-size: 0.82rem; color: var(--color-text-muted); }
        .scope-form input { padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); color: var(--color-text-main); }
        .scope-pending { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
        .scope-ok { color: #10b981; }
        .muted { color: var(--color-text-muted); font-size: 0.88rem; }
        .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding-top: 8px; }
        .action-link { display: inline-flex; align-items: center; gap: 8px; text-decoration: none; }
        .error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
        .empty-state { display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--color-text-muted); padding: 48px; }
        :global(.spin-icon) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

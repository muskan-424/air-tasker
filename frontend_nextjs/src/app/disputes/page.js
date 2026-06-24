"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, Gavel, Loader, ShieldAlert } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { reportsAPI, tasksAPI } from "@/lib/api";

const REPORT_CATEGORIES = [
  { value: "fraud", label: "Fraud / scam" },
  { value: "harassment", label: "Harassment" },
  { value: "spam", label: "Spam" },
  { value: "safety", label: "Safety concern" },
  { value: "other", label: "Other" },
];

function DisputesInner() {
  const { isLoggedIn } = useAuth();
  const searchParams = useSearchParams();
  const urlTaskId = searchParams?.get("task_id") || "";

  const [taskId, setTaskId] = useState(urlTaskId);
  const [reason, setReason] = useState("");
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [reportCategory, setReportCategory] = useState("fraud");
  const [reportReason, setReportReason] = useState("");
  const [reportSubmitting, setReportSubmitting] = useState(false);

  useEffect(() => {
    if (urlTaskId) setTaskId(urlTaskId);
  }, [urlTaskId]);

  useEffect(() => {
    if (!taskId.trim() || !isLoggedIn) {
      setDisputes([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    tasksAPI
      .listDisputes(taskId.trim())
      .then((data) => { if (!cancelled) setDisputes(data || []); })
      .catch(() => { if (!cancelled) setDisputes([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [taskId, isLoggedIn]);

  const handleOpen = async (e) => {
    e.preventDefault();
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    if (!taskId.trim()) { setError("Enter a task ID."); return; }
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await tasksAPI.openDispute(taskId.trim(), reason.trim() || null);
      setSuccess(`Dispute opened · ID ${data.dispute_id.slice(0, 8)}…`);
      const list = await tasksAPI.listDisputes(taskId.trim());
      setDisputes(list || []);
      setReason("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReport = async (e) => {
    e.preventDefault();
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    if (!taskId.trim() && !reportReason.trim()) {
      setError("Enter a task ID or detailed report reason.");
      return;
    }
    if (reportReason.trim().length < 10) {
      setError("Report reason must be at least 10 characters.");
      return;
    }
    setReportSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await reportsAPI.create({
        taskId: taskId.trim() || null,
        category: reportCategory,
        reason: reportReason.trim(),
      });
      const flags = data.trust_flags_raised?.length
        ? ` · Trust review: ${data.trust_flags_raised.join(", ")}`
        : "";
      setSuccess(`Report submitted · ID ${data.report_id.slice(0, 8)}…${flags}`);
      setReportReason("");
    } catch (err) {
      setError(err.message);
    } finally {
      setReportSubmitting(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card"><p>Please <Link href="/login">sign in</Link> to manage disputes.</p></div>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header>
        <h1><Gavel size={26} /> Disputes</h1>
        <p>Open a dispute on a task when verification fails or work is contested. Escrow moves to dispute status.</p>
      </header>

      {error && <div className="banner err"><AlertTriangle size={16} /> {error}</div>}
      {success && <div className="banner ok">{success}</div>}

      <form onSubmit={handleOpen} className="glass-card form-card">
        <label>
          Task ID
          <input value={taskId} onChange={(e) => setTaskId(e.target.value)} placeholder="UUID" required />
        </label>
        <label>
          Reason (optional)
          <textarea
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Describe the issue — e.g. incomplete work, wrong evidence…"
          />
        </label>
        <button type="submit" className="btn-premium btn-saffron" disabled={submitting}>
          <ShieldAlert size={16} />
          {submitting ? "Opening…" : "Open dispute"}
        </button>
        <p className="hint">Poster or assigned tasker can open a dispute. Admins resolve on the <Link href="/admin">Admin dashboard</Link>.</p>
      </form>

      <form onSubmit={handleReport} className="glass-card form-card report-card">
        <h2>Report user or task</h2>
        <p className="hint">Use for fraud, harassment, or safety issues. Ops reviews reports in Admin → Reports.</p>
        <label>
          Category
          <select value={reportCategory} onChange={(e) => setReportCategory(e.target.value)}>
            {REPORT_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </label>
        <label>
          Details (required, min 10 chars)
          <textarea
            rows={3}
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value)}
            placeholder="Describe what happened — include dates, messages, or payment requests outside escrow…"
          />
        </label>
        <button type="submit" className="btn-premium btn-outline" disabled={reportSubmitting}>
          {reportSubmitting ? "Submitting…" : "Submit report"}
        </button>
      </form>

      <div className="glass-card list-card">
        <h2>Dispute history</h2>
        {loading ? (
          <div className="empty"><Loader className="spin" size={20} /> Loading…</div>
        ) : !taskId.trim() ? (
          <p className="muted">Enter a task ID to view disputes.</p>
        ) : disputes.length === 0 ? (
          <p className="muted">No disputes for this task yet.</p>
        ) : (
          <ul>
            {disputes.map((d) => (
              <li key={d.dispute_id} className={d.status === "OPEN" ? "open" : ""}>
                <div className="row-top">
                  <span className={`status ${d.status.toLowerCase()}`}>{d.status}</span>
                  <time>{new Date(d.created_at).toLocaleString()}</time>
                </div>
                <p className="id">ID: <code>{d.dispute_id}</code></p>
                {d.reason && <p className="reason">{d.reason}</p>}
                {d.status === "OPEN" && (
                  <Link href="/admin" className="admin-link">Awaiting admin review →</Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <style jsx>{`
        .page-shell { max-width: 640px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        h1 { display: flex; align-items: center; gap: 10px; font-size: 1.75rem; font-weight: 800; }
        header p { color: var(--color-text-muted); margin-top: 8px; font-size: 0.9rem; }
        .banner { padding: 12px 16px; border-radius: 10px; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; }
        .banner.err { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
        .banner.ok { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25); color: #6ee7b7; }
        .form-card, .list-card { padding: 24px; display: flex; flex-direction: column; gap: 14px; }
        .report-card h2 { font-size: 1rem; font-weight: 700; }
        select {
          background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px;
          padding: 11px 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.9rem;
        }
        label { display: flex; flex-direction: column; gap: 6px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); }
        input, textarea {
          background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px;
          padding: 11px 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.9rem;
        }
        .hint { font-size: 0.78rem; color: var(--color-text-muted); }
        .hint a { color: var(--color-teal); }
        .list-card h2 { font-size: 1rem; font-weight: 700; }
        ul { list-style: none; display: flex; flex-direction: column; gap: 12px; }
        li { padding: 14px; border-radius: 10px; border: 1px solid var(--border-glow); background: rgba(255,255,255,0.02); }
        li.open { border-color: rgba(245,158,11,0.3); background: rgba(245,158,11,0.04); }
        .row-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .status { font-size: 0.68rem; font-weight: 800; padding: 3px 8px; border-radius: 6px; }
        .status.open { color: #f59e0b; background: rgba(245,158,11,0.15); }
        .status.resolved { color: #10b981; background: rgba(16,185,129,0.12); }
        time { font-size: 0.72rem; color: var(--color-text-muted); }
        .id code { color: var(--color-teal); font-size: 0.75rem; }
        .reason { font-size: 0.85rem; color: var(--color-text-muted); margin-top: 6px; }
        .admin-link { font-size: 0.78rem; color: var(--color-saffron); margin-top: 8px; display: inline-block; }
        .muted, .empty { color: var(--color-text-muted); font-size: 0.85rem; }
        .empty { display: flex; align-items: center; gap: 8px; }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

export default function DisputesPage() {
  return (
    <Suspense fallback={<main className="page-shell"><div className="glass-card">Loading…</div></main>}>
      <DisputesInner />
    </Suspense>
  );
}

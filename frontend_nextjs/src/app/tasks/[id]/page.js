"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Loader2,
  MapPin,
  ShieldCheck,
  Timer,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { tasksAPI } from "@/lib/api";

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params?.id;
  const { isLoggedIn, user } = useAuth();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (!taskId || !isLoggedIn) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await tasksAPI.get(taskId);
        if (!cancelled) setTask(data);
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setTask(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [taskId, isLoggedIn]);

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await tasksAPI.accept(taskId);
      window.location.href = `/payments?task_id=${taskId}`;
    } catch (err) {
      alert(`Accept failed: ${err.message}`);
    } finally {
      setAccepting(false);
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
  const canAccept = isTasker && task.status === "PUBLISHED";

  return (
    <main className="page-shell">
      <Link href={isTasker ? "/tasker" : "/my-tasks"} className="back-link">
        <ArrowLeft size={16} /> Back
      </Link>

      <div className="glass-card detail-card">
        <div className="detail-top">
          <span className="cat-chip">{task.category || "General"}</span>
          <span className="status-chip">{task.status}</span>
        </div>

        <h1>{schema.title || task.subcategory || "Task"}</h1>
        <p className="desc">{schema.description || "No description provided."}</p>

        <div className="meta-grid">
          <div><MapPin size={16} /> {schema.location || schema.location_pin || "India"}</div>
          <div><Timer size={16} /> {schema.estimated_duration_minutes || 60} min</div>
          {price.min != null && (
            <div><CreditCard size={16} /> ₹{price.min}–₹{price.max || price.min}</div>
          )}
        </div>

        {schema.completion_criteria && (
          <section className="section">
            <h3>Completion criteria</h3>
            <p>{schema.completion_criteria}</p>
          </section>
        )}

        {schema.evidence_requirements && (
          <section className="section">
            <h3>Evidence required</h3>
            <p>{JSON.stringify(schema.evidence_requirements)}</p>
          </section>
        )}

        <p className="task-id">Task ID: <code>{task.id}</code></p>

        <div className="actions">
          {canAccept && (
            <button type="button" className="btn-premium btn-saffron" onClick={handleAccept} disabled={accepting}>
              {accepting ? "Accepting..." : "Accept Task"}
            </button>
          )}
          <Link href={`/verify?task_id=${task.id}`} className="btn-premium btn-teal action-link">
            <ShieldCheck size={16} /> Upload Evidence
          </Link>
          <Link href={`/payments?task_id=${task.id}`} className="btn-premium btn-teal action-link">
            <CreditCard size={16} /> Payments & Escrow
          </Link>
          {task.status === "ACCEPTED" && (
            <span className="accepted-note"><CheckCircle2 size={16} /> Task accepted</span>
          )}
        </div>
      </div>

      <style jsx>{`
        .page-shell { max-width: 760px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .back-link { display: inline-flex; align-items: center; gap: 6px; color: var(--color-text-muted); text-decoration: none; font-size: 0.9rem; }
        .back-link:hover { color: var(--color-teal); }
        .detail-card { padding: 28px; display: flex; flex-direction: column; gap: 16px; }
        .detail-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
        .cat-chip { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--color-teal); }
        .status-chip { font-size: 0.72rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border-teal); color: var(--color-teal); }
        h1 { font-size: 1.8rem; font-weight: 800; }
        .desc { color: var(--color-text-muted); line-height: 1.6; }
        .meta-grid { display: flex; flex-wrap: wrap; gap: 16px; color: var(--color-text-muted); font-size: 0.88rem; }
        .meta-grid div { display: flex; align-items: center; gap: 6px; }
        .section h3 { font-size: 0.95rem; margin-bottom: 6px; }
        .section p { color: var(--color-text-muted); font-size: 0.88rem; line-height: 1.5; }
        .task-id { font-size: 0.78rem; color: var(--color-text-muted); }
        .task-id code { color: var(--color-teal); }
        .actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding-top: 8px; }
        .action-link { display: inline-flex; align-items: center; gap: 8px; text-decoration: none; }
        .accepted-note { display: inline-flex; align-items: center; gap: 6px; color: #10b981; font-size: 0.88rem; font-weight: 600; }
        .error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
        .empty-state { display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--color-text-muted); padding: 48px; }
        :global(.spin-icon) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

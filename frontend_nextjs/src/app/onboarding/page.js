"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, Loader2, Rocket, RefreshCw } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { onboardingAPI } from "@/lib/api";

export default function OnboardingPage() {
  const { isLoggedIn, user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!isLoggedIn) return;
    setLoading(true);
    setError(null);
    try {
      const res = await onboardingAPI.get();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    load();
  }, [load]);

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <p>Please <Link href="/login">sign in</Link> to continue setup.</p>
      </main>
    );
  }

  const pct = data ? Math.round((data.completed_count / Math.max(data.total_count, 1)) * 100) : 0;
  const isTasker = user?.role === "TASKER" || data?.role === "TASKER";

  return (
    <main className="page-shell">
      <header className="header">
        <Rocket size={28} style={{ color: "var(--color-teal)" }} />
        <div>
          <h1>Get ready for beta</h1>
          <p>
            {isTasker
              ? "Complete these steps to accept jobs and get paid."
              : "Complete these steps to post tasks and pay securely."}
          </p>
        </div>
        <button type="button" className="btn-premium btn-teal refresh-btn" onClick={load} disabled={loading}>
          <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
        </button>
      </header>

      {error && <div className="error-bar">{error}</div>}

      {loading && !data ? (
        <div className="empty"><Loader2 className="spin" size={22} /> Loading checklist…</div>
      ) : data && (
        <>
          <div className="progress-card glass-card">
            <div className="progress-top">
              <span>{data.completed_count} of {data.total_count} required steps done</span>
              <strong>{pct}%</strong>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
            {data.complete && (
              <p className="complete-msg">You&apos;re all set — start using VayuTask!</p>
            )}
          </div>

          {data.beta_pin_codes?.length > 0 && (
            <div className="beta-hint glass-card">
              <strong>Closed beta areas</strong>
              <span>PINs: {data.beta_pin_codes.join(", ")}</span>
              <span>Categories: {data.beta_categories?.join(", ")}</span>
            </div>
          )}

          <ul className="steps-list">
            {data.steps.map((step) => (
              <li key={step.id} className={`step-card glass-card ${step.complete ? "done" : ""}`}>
                <div className="step-icon">
                  {step.complete ? (
                    <CheckCircle2 size={22} color="#10b981" />
                  ) : (
                    <Circle size={22} color="var(--color-text-muted)" />
                  )}
                </div>
                <div className="step-body">
                  <div className="step-title-row">
                    <h3>{step.title}</h3>
                    {step.optional && <span className="optional-tag">Optional</span>}
                  </div>
                  <p>{step.description}</p>
                  {step.href && !step.complete && (
                    <Link href={step.href} className="step-link">
                      Continue →
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ul>

          <div className="cta-row">
            {data.complete ? (
              <Link href={isTasker ? "/tasker" : "/poster"} className="btn-premium btn-teal">
                {isTasker ? "Open tasker radar" : "Post a task"}
              </Link>
            ) : (
              <Link href="/account" className="btn-premium btn-teal">
                Start with email verification
              </Link>
            )}
            <Link href="/my-tasks" className="btn-premium btn-outline">
              Go to my tasks
            </Link>
          </div>
        </>
      )}

      <style jsx>{`
        .page-shell { max-width: 720px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .header { display: flex; gap: 16px; align-items: flex-start; }
        .header h1 { font-size: 1.7rem; font-weight: 800; }
        .header p { color: var(--color-text-muted); font-size: 0.9rem; margin-top: 4px; }
        .refresh-btn { margin-left: auto; padding: 10px 12px; }
        .progress-card { padding: 20px; display: flex; flex-direction: column; gap: 10px; }
        .progress-top { display: flex; justify-content: space-between; font-size: 0.88rem; color: var(--color-text-muted); }
        .progress-top strong { color: var(--color-teal); }
        .progress-track { height: 8px; border-radius: 999px; background: rgba(255,255,255,0.06); overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--color-teal), #14b8a6); border-radius: 999px; transition: width 0.4s ease; }
        .complete-msg { color: #10b981; font-size: 0.88rem; font-weight: 600; }
        .beta-hint { padding: 14px 18px; display: flex; flex-direction: column; gap: 4px; font-size: 0.82rem; color: var(--color-text-muted); }
        .beta-hint strong { color: var(--color-saffron); font-size: 0.78rem; text-transform: uppercase; }
        .steps-list { list-style: none; display: flex; flex-direction: column; gap: 12px; padding: 0; margin: 0; }
        .step-card { display: flex; gap: 14px; padding: 18px; }
        .step-card.done { border-color: rgba(16,185,129,0.25); }
        .step-body { flex: 1; }
        .step-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
        .step-body h3 { font-size: 1rem; font-weight: 700; }
        .step-body p { font-size: 0.85rem; color: var(--color-text-muted); line-height: 1.45; }
        .optional-tag { font-size: 0.65rem; padding: 2px 8px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.12); color: var(--color-text-muted); }
        .step-link { display: inline-block; margin-top: 8px; color: var(--color-teal); font-size: 0.85rem; font-weight: 600; text-decoration: none; }
        .cta-row { display: flex; flex-wrap: wrap; gap: 10px; padding-top: 8px; }
        .error-bar { padding: 12px; border-radius: 10px; background: rgba(239,68,68,0.08); color: #fca5a5; font-size: 0.88rem; }
        .empty { display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--color-text-muted); padding: 40px; }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

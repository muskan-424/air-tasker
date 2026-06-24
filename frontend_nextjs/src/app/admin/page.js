"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Gavel, Loader, Shield, XCircle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { accountAPI, kycAPI, tasksAPI } from "@/lib/api";

const ADMIN_ROLES = new Set(["ADMIN", "REVIEWER"]);

export default function AdminPage() {
  const { isLoggedIn, user } = useAuth();
  const [role, setRole] = useState(user?.role || null);
  const [tab, setTab] = useState("disputes");
  const [disputes, setDisputes] = useState([]);
  const [kycQueue, setKycQueue] = useState([]);
  const [verifications, setVerifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!isLoggedIn) return;
    accountAPI.me().then((d) => setRole(d.role)).catch(() => {});
  }, [isLoggedIn]);

  const isAdmin = ADMIN_ROLES.has(role || user?.role);

  const loadQueues = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const [d, k, v] = await Promise.all([
        tasksAPI.listOpenDisputes(),
        kycAPI.listPending(),
        tasksAPI.listReviewVerifications(),
      ]);
      setDisputes(d || []);
      setKycQueue(k || []);
      setVerifications(v || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    loadQueues();
  }, [loadQueues]);

  const resolveDispute = async (disputeId, outcome) => {
    setActing(disputeId + outcome);
    setError(null);
    try {
      await tasksAPI.resolveDispute(disputeId, outcome, `Admin ${outcome} via dashboard`);
      setSuccess(`Dispute resolved (${outcome})`);
      await loadQueues();
    } catch (err) {
      setError(err.message);
    } finally {
      setActing(null);
    }
  };

  const reviewKyc = async (userId, decision) => {
    setActing(userId + decision);
    setError(null);
    try {
      await kycAPI.review(userId, decision, decision === "reject" ? "Rejected from admin dashboard" : null);
      setSuccess(`KYC ${decision}d`);
      await loadQueues();
    } catch (err) {
      setError(err.message);
    } finally {
      setActing(null);
    }
  };

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card"><p>Please <Link href="/login">sign in</Link>.</p></div>
      </main>
    );
  }

  if (!isAdmin) {
    return (
      <main className="page-shell">
        <div className="glass-card">
          <p>Admin dashboard requires an <b>ADMIN</b> or <b>REVIEWER</b> account. Register with that role or ask ops to upgrade your user.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header>
        <h1><Shield size={26} /> Admin Dashboard</h1>
        <p>Resolve disputes, review KYC, and triage low-confidence verifications.</p>
      </header>

      {error && <div className="banner err">{error}</div>}
      {success && <div className="banner ok">{success}</div>}

      <div className="tabs">
        {[
          ["disputes", `Disputes (${disputes.length})`],
          ["kyc", `KYC (${kycQueue.length})`],
          ["verify", `Review (${verifications.length})`],
        ].map(([key, label]) => (
          <button key={key} type="button" className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="glass-card empty"><Loader className="spin" size={22} /> Loading queues…</div>
      ) : tab === "disputes" ? (
        <div className="glass-card queue">
          {disputes.length === 0 ? <p className="muted">No open disputes.</p> : disputes.map((d) => (
            <article key={d.dispute_id} className="item">
              <div className="top">
                <Gavel size={16} />
                <span>Task <code>{d.task_id.slice(0, 8)}…</code></span>
                <time>{new Date(d.created_at).toLocaleString()}</time>
              </div>
              {d.reason && <p>{d.reason}</p>}
              <div className="actions">
                <button type="button" className="btn-premium btn-teal" disabled={!!acting} onClick={() => resolveDispute(d.dispute_id, "release")}>
                  Release to tasker
                </button>
                <button type="button" className="btn-premium btn-outline" disabled={!!acting} onClick={() => resolveDispute(d.dispute_id, "cancel")}>
                  Cancel / refund poster
                </button>
                <Link href={`/payments?task_id=${d.task_id}`} className="link">Payments</Link>
              </div>
            </article>
          ))}
        </div>
      ) : tab === "kyc" ? (
        <div className="glass-card queue">
          {kycQueue.length === 0 ? <p className="muted">No pending KYC.</p> : kycQueue.map((k) => (
            <article key={k.user_id || k.pan_masked} className="item">
              <div className="top"><strong>{k.full_name}</strong> · PAN {k.pan_masked}</div>
              <p className="meta">User {k.user_id?.slice(0, 8)}… · {k.provider}</p>
              <div className="actions">
                <button type="button" className="btn-premium btn-teal" disabled={!!acting} onClick={() => reviewKyc(k.user_id, "approve")}>
                  <CheckCircle2 size={14} /> Approve
                </button>
                <button type="button" className="btn-premium btn-outline" disabled={!!acting} onClick={() => reviewKyc(k.user_id, "reject")}>
                  <XCircle size={14} /> Reject
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="glass-card queue">
          {verifications.length === 0 ? <p className="muted">No verifications needing review.</p> : verifications.map((v) => (
            <article key={v.verification_id} className="item">
              <div className="top">
                <span className={`badge ${v.status.toLowerCase()}`}>{v.status}</span>
                <span>{Math.round(v.confidence * 100)}% confidence</span>
              </div>
              <p className="meta">Task <code>{v.task_id.slice(0, 8)}…</code></p>
              {v.explanation && <p>{v.explanation}</p>}
              <div className="actions">
                <Link href={`/verify?task_id=${v.task_id}`} className="link">View evidence</Link>
                <Link href={`/disputes?task_id=${v.task_id}`} className="link">Open dispute</Link>
              </div>
            </article>
          ))}
        </div>
      )}

      <style jsx>{`
        .page-shell { max-width: 800px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        h1 { display: flex; align-items: center; gap: 10px; font-size: 1.75rem; font-weight: 800; }
        header p { color: var(--color-text-muted); margin-top: 8px; }
        .banner { padding: 12px 16px; border-radius: 10px; font-size: 0.85rem; }
        .banner.err { background: rgba(239,68,68,0.08); color: #fca5a5; border: 1px solid rgba(239,68,68,0.25); }
        .banner.ok { background: rgba(16,185,129,0.08); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.25); }
        .tabs { display: flex; flex-wrap: wrap; gap: 8px; }
        .tabs button {
          padding: 8px 14px; border-radius: 999px; border: 1px solid var(--border-glow);
          background: transparent; color: var(--color-text-muted); font-size: 0.8rem; font-weight: 700; cursor: pointer; font-family: inherit;
        }
        .tabs button.active { color: var(--color-teal); border-color: var(--border-teal); background: rgba(20,184,166,0.08); }
        .queue { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
        .item { padding: 16px; border-radius: 10px; border: 1px solid var(--border-glow); background: rgba(255,255,255,0.02); }
        .top { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 0.88rem; margin-bottom: 8px; }
        .meta { font-size: 0.78rem; color: var(--color-text-muted); }
        code { color: var(--color-teal); font-size: 0.75rem; }
        .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; align-items: center; }
        .link { font-size: 0.78rem; color: var(--color-teal); text-decoration: underline; }
        .badge { font-size: 0.65rem; font-weight: 800; padding: 3px 8px; border-radius: 6px; text-transform: uppercase; }
        .badge.low_confidence { color: #f59e0b; background: rgba(245,158,11,0.15); }
        .badge.fail { color: #ef4444; background: rgba(239,68,68,0.12); }
        .muted, .empty { color: var(--color-text-muted); }
        .empty { display: flex; align-items: center; gap: 8px; padding: 24px; }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

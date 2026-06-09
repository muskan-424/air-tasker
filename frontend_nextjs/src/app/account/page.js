"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader, Mail, Shield, AlertTriangle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { accountAPI, verificationAPI } from "@/lib/api";

function formatVerifiedAt(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function AccountPage() {
  const { isLoggedIn, user, setUserVerified } = useAuth();
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [ttlSeconds, setTtlSeconds] = useState(0);
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const loadAccount = useCallback(async () => {
    if (!isLoggedIn) return;
    setLoading(true);
    setError(null);
    try {
      const data = await accountAPI.me();
      setAccount(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    loadAccount();
  }, [loadAccount]);

  useEffect(() => {
    if (ttlSeconds <= 0) return undefined;
    const id = setInterval(() => {
      setTtlSeconds((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [ttlSeconds]);

  const handleSendOtp = async () => {
    setSending(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await verificationAPI.requestEmailOtp("EMAIL_VERIFICATION");
      setOtpSent(true);
      setTtlSeconds(res.ttl_seconds || 600);
      setSuccess("Verification code sent. Check your inbox — or backend logs if SMTP is not configured.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    const trimmed = code.replace(/\s/g, "");
    if (trimmed.length < 4) {
      setError("Enter the 6-digit code from your email.");
      return;
    }
    setVerifying(true);
    setError(null);
    setSuccess(null);
    try {
      await verificationAPI.verifyEmailOtp(trimmed, "EMAIL_VERIFICATION");
      setSuccess("Email verified successfully.");
      setCode("");
      setOtpSent(false);
      setUserVerified?.(true);
      await loadAccount();
    } catch (err) {
      setError(err.message);
    } finally {
      setVerifying(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card page-card">
          <p>Please <Link href="/login">sign in</Link> to manage your account.</p>
        </div>
      </main>
    );
  }

  const verified = Boolean(account?.email_verified_at);

  return (
    <main className="page-shell">
      <header className="page-header">
        <h1><Shield size={28} /> Account Security</h1>
        <p>Verify your email to unlock trust features and sensitive actions.</p>
      </header>

      {error && (
        <div className="banner error"><AlertTriangle size={16} /> {error}</div>
      )}
      {success && (
        <div className="banner success"><CheckCircle2 size={16} /> {success}</div>
      )}

      <div className="glass-card account-card">
        {loading ? (
          <div className="empty"><Loader className="spin" size={22} /> Loading account…</div>
        ) : (
          <>
            <section className="section">
              <h2>Email address</h2>
              <div className="email-row">
                <Mail size={18} />
                <span>{account?.email || user?.email}</span>
                {verified ? (
                  <span className="badge verified"><CheckCircle2 size={14} /> Verified</span>
                ) : (
                  <span className="badge pending">Not verified</span>
                )}
              </div>
              {verified && account?.email_verified_at && (
                <p className="meta">Verified on {formatVerifiedAt(account.email_verified_at)}</p>
              )}
            </section>

            {!verified && (
              <section className="section otp-section">
                <h2>Email verification (OTP)</h2>
                <p className="hint">
                  We send a 6-digit code to your email. In local dev without SMTP, check the
                  FastAPI terminal for <code>[email stub]</code> log lines.
                </p>

                <button
                  type="button"
                  className="btn-premium btn-teal"
                  onClick={handleSendOtp}
                  disabled={sending}
                >
                  {sending ? "Sending…" : otpSent ? "Resend code" : "Send verification code"}
                </button>

                {otpSent && ttlSeconds > 0 && (
                  <p className="ttl">Code expires in {Math.floor(ttlSeconds / 60)}:{String(ttlSeconds % 60).padStart(2, "0")}</p>
                )}

                <form onSubmit={handleVerify} className="otp-form">
                  <label htmlFor="otp-code">Enter 6-digit code</label>
                  <input
                    id="otp-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={8}
                    placeholder="123456"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/[^\d]/g, ""))}
                    className="otp-input"
                  />
                  <button
                    type="submit"
                    className="btn-premium btn-saffron"
                    disabled={verifying || code.length < 4}
                  >
                    {verifying ? "Verifying…" : "Verify email"}
                  </button>
                </form>
              </section>
            )}

            <section className="section">
              <h2>Account details</h2>
              <dl className="details">
                <div><dt>Role</dt><dd>{account?.role || user?.role || "—"}</dd></div>
                <div><dt>User ID</dt><dd><code>{account?.id || user?.id || "—"}</code></dd></div>
              </dl>
            </section>
          </>
        )}
      </div>

      <style jsx>{`
        .page-shell { max-width: 640px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .page-header h1 { display: flex; align-items: center; gap: 10px; font-size: 1.8rem; font-weight: 800; }
        .page-header p { color: var(--color-text-muted); margin-top: 8px; font-size: 0.9rem; }
        .banner { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-radius: 10px; font-size: 0.85rem; }
        .banner.error { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
        .banner.success { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25); color: #6ee7b7; }
        .account-card { padding: 28px; display: flex; flex-direction: column; gap: 28px; }
        .section h2 { font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; border-left: 3px solid var(--color-teal); padding-left: 10px; }
        .email-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 0.95rem; }
        .badge { display: inline-flex; align-items: center; gap: 4px; font-size: 0.72rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; margin-left: auto; }
        .badge.verified { color: #10b981; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25); }
        .badge.pending { color: var(--color-saffron); background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.25); }
        .meta { font-size: 0.78rem; color: var(--color-text-muted); margin-top: 8px; }
        .hint { font-size: 0.82rem; color: var(--color-text-muted); line-height: 1.5; margin-bottom: 16px; }
        .hint code { color: var(--color-teal); font-size: 0.78rem; }
        .ttl { font-size: 0.78rem; color: var(--color-saffron); margin-top: 10px; }
        .otp-form { display: flex; flex-direction: column; gap: 10px; margin-top: 20px; padding-top: 20px; border-top: 1px dashed var(--border-glow); }
        .otp-form label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); }
        .otp-input {
          background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 10px;
          padding: 14px 16px; font-size: 1.4rem; letter-spacing: 0.3em; text-align: center;
          color: var(--color-text-main); font-family: monospace; outline: none; max-width: 220px;
        }
        .otp-input:focus { border-color: var(--color-teal); }
        .details { display: flex; flex-direction: column; gap: 10px; }
        .details div { display: flex; justify-content: space-between; gap: 12px; font-size: 0.85rem; }
        dt { color: var(--color-text-muted); }
        dd code { color: var(--color-teal); font-size: 0.75rem; word-break: break-all; }
        .empty { display: flex; align-items: center; gap: 10px; color: var(--color-text-muted); padding: 24px 0; }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

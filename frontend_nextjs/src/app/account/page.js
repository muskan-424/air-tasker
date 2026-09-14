"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader, Mail, Phone, Shield, AlertTriangle } from "lucide-react";
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
  const [isLocalDev, setIsLocalDev] = useState(false);

  // Phone verification — kept separate from email state so the two flows don't clash.
  const [phoneInput, setPhoneInput] = useState("");
  const [phoneCode, setPhoneCode] = useState("");
  const [phoneOtpSent, setPhoneOtpSent] = useState(false);
  const [phoneTtlSeconds, setPhoneTtlSeconds] = useState(0);
  const [phoneSending, setPhoneSending] = useState(false);
  const [phoneVerifying, setPhoneVerifying] = useState(false);
  const [phoneError, setPhoneError] = useState(null);
  const [phoneSuccess, setPhoneSuccess] = useState(null);

  useEffect(() => {
    const host = window.location.hostname;
    setIsLocalDev(host === "localhost" || host === "127.0.0.1");
  }, []);

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

  useEffect(() => {
    if (phoneTtlSeconds <= 0) return undefined;
    const id = setInterval(() => {
      setPhoneTtlSeconds((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [phoneTtlSeconds]);

  useEffect(() => {
    if (account?.phone) setPhoneInput(account.phone);
  }, [account?.phone]);

  const handleSendOtp = async () => {
    setSending(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await verificationAPI.requestEmailOtp("EMAIL_VERIFICATION");
      setOtpSent(true);
      setTtlSeconds(res.ttl_seconds || 600);
      if (res.delivery === "sent") {
        setSuccess("Verification code sent to your email.");
      } else if (isLocalDev) {
        setSuccess("Code generated — check the server terminal for [email stub] if SMTP is not configured.");
      } else {
        setSuccess("Code generated. Email delivery is not configured on this server — contact support.");
      }
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

  const handleSendPhoneOtp = async () => {
    const trimmedPhone = phoneInput.replace(/\s/g, "");
    if (trimmedPhone.length < 10) {
      setPhoneError("Enter a valid 10-digit mobile number.");
      return;
    }
    setPhoneSending(true);
    setPhoneError(null);
    setPhoneSuccess(null);
    try {
      // Only send the phone when it's new/changed — resending to an unchanged number just needs a code.
      const res = await verificationAPI.requestPhoneOtp(
        trimmedPhone !== account?.phone ? trimmedPhone : null
      );
      setPhoneOtpSent(true);
      setPhoneTtlSeconds(res.ttl_seconds || 600);
      if (res.delivery === "sent") {
        setPhoneSuccess("Verification code sent by SMS.");
      } else if (isLocalDev) {
        setPhoneSuccess("Code generated — check the server terminal for [sms stub], no SMS gateway is configured yet.");
      } else {
        setPhoneSuccess("Code generated. SMS delivery is not configured on this server — contact support.");
      }
    } catch (err) {
      setPhoneError(err.message);
    } finally {
      setPhoneSending(false);
    }
  };

  const handleVerifyPhone = async (e) => {
    e.preventDefault();
    const trimmed = phoneCode.replace(/\s/g, "");
    if (trimmed.length < 4) {
      setPhoneError("Enter the 6-digit code from the SMS.");
      return;
    }
    setPhoneVerifying(true);
    setPhoneError(null);
    setPhoneSuccess(null);
    try {
      await verificationAPI.verifyPhoneOtp(trimmed);
      setPhoneSuccess("Phone number verified successfully.");
      setPhoneCode("");
      setPhoneOtpSent(false);
      await loadAccount();
    } catch (err) {
      setPhoneError(err.message);
    } finally {
      setPhoneVerifying(false);
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
  const phoneVerified = Boolean(account?.phone_verified_at);

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
                  We send a 6-digit code to your email. Enter it below to verify your account.
                </p>
                {isLocalDev && (
                  <p className="hint dev-hint">
                    Local dev: if email does not arrive, check the server terminal for{" "}
                    <code>[email stub]</code> log lines.
                  </p>
                )}

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
              <h2>Phone number</h2>
              {phoneError && (
                <div className="banner error"><AlertTriangle size={16} /> {phoneError}</div>
              )}
              {phoneSuccess && (
                <div className="banner success"><CheckCircle2 size={16} /> {phoneSuccess}</div>
              )}
              <div className="email-row">
                <Phone size={18} />
                <span>{account?.phone ? `+91 ${account.phone}` : "Not added"}</span>
                {phoneVerified ? (
                  <span className="badge verified"><CheckCircle2 size={14} /> Verified</span>
                ) : (
                  <span className="badge pending">Not verified</span>
                )}
              </div>
              {phoneVerified && account?.phone_verified_at && (
                <p className="meta">Verified on {formatVerifiedAt(account.phone_verified_at)}</p>
              )}

              {!phoneVerified && (
                <div className="otp-section">
                  <p className="hint">
                    We send a 6-digit code by SMS to verify your number. Used for tasker payouts and
                    account recovery.
                  </p>
                  {isLocalDev && (
                    <p className="hint dev-hint">
                      Local dev: no SMS gateway is configured — check the server terminal for{" "}
                      <code>[sms stub]</code> log lines.
                    </p>
                  )}

                  <label htmlFor="phone-input" className="phone-label">10-digit mobile number</label>
                  <div className="phone-input-row">
                    <span className="phone-prefix">+91</span>
                    <input
                      id="phone-input"
                      type="tel"
                      inputMode="numeric"
                      maxLength={10}
                      placeholder="9876543210"
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value.replace(/[^\d]/g, ""))}
                      className="otp-input phone-input"
                    />
                  </div>

                  <button
                    type="button"
                    className="btn-premium btn-teal"
                    onClick={handleSendPhoneOtp}
                    disabled={phoneSending}
                  >
                    {phoneSending ? "Sending…" : phoneOtpSent ? "Resend code" : "Send verification code"}
                  </button>

                  {phoneOtpSent && phoneTtlSeconds > 0 && (
                    <p className="ttl">Code expires in {Math.floor(phoneTtlSeconds / 60)}:{String(phoneTtlSeconds % 60).padStart(2, "0")}</p>
                  )}

                  <form onSubmit={handleVerifyPhone} className="otp-form">
                    <label htmlFor="phone-otp-code">Enter 6-digit code</label>
                    <input
                      id="phone-otp-code"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={8}
                      placeholder="123456"
                      value={phoneCode}
                      onChange={(e) => setPhoneCode(e.target.value.replace(/[^\d]/g, ""))}
                      className="otp-input"
                    />
                    <button
                      type="submit"
                      className="btn-premium btn-saffron"
                      disabled={phoneVerifying || phoneCode.length < 4}
                    >
                      {phoneVerifying ? "Verifying…" : "Verify phone"}
                    </button>
                  </form>
                </div>
              )}
            </section>

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
        .phone-label { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); display: block; margin-bottom: 8px; }
        .phone-input-row { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; max-width: 220px; }
        .phone-prefix { color: var(--color-text-muted); font-family: monospace; font-size: 0.95rem; }
        .phone-input { max-width: 170px; font-size: 1rem; letter-spacing: 0.1em; padding: 10px 14px; }
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

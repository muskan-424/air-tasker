"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  Clock,
  Loader,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { kycAPI, paymentsAPI } from "@/lib/api";

const KYC_STATUS = {
  none: { label: "Not submitted", color: "#94a3b8", icon: AlertTriangle },
  pending: { label: "Under review", color: "#f59e0b", icon: Clock },
  verified: { label: "Verified", color: "#10b981", icon: CheckCircle2 },
  rejected: { label: "Rejected", color: "#ef4444", icon: XCircle },
};

export default function KycPayoutPage() {
  const { isLoggedIn, user } = useAuth();
  const isTasker = user?.role === "TASKER";

  const [kyc, setKyc] = useState(null);
  const [payout, setPayout] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [kycForm, setKycForm] = useState({ full_name: "", pan: "", aadhaar_last4: "" });
  const [bankForm, setBankForm] = useState({ beneficiary_name: "", ifsc: "", account_number: "" });
  const [submittingKyc, setSubmittingKyc] = useState(false);
  const [submittingBank, setSubmittingBank] = useState(false);

  const loadAll = useCallback(async () => {
    if (!isLoggedIn || !isTasker) return;
    setLoading(true);
    setError(null);
    try {
      const [kycData, payoutData] = await Promise.all([
        kycAPI.status(),
        paymentsAPI.payoutStatus(),
      ]);
      setKyc(kycData);
      setPayout(payoutData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn, isTasker]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleKycSubmit = async (e) => {
    e.preventDefault();
    setSubmittingKyc(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await kycAPI.submit(
        kycForm.full_name.trim(),
        kycForm.pan.trim().toUpperCase(),
        kycForm.aadhaar_last4.trim() || null
      );
      setKyc(data);
      setSuccess(
        data.status === "verified"
          ? "KYC verified (stub provider auto-approved in dev)."
          : "KYC submitted — pending admin review."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingKyc(false);
    }
  };

  const handleBankSubmit = async (e) => {
    e.preventDefault();
    setSubmittingBank(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await paymentsAPI.registerPayoutBank(
        bankForm.beneficiary_name.trim(),
        bankForm.ifsc.trim(),
        bankForm.account_number.trim()
      );
      setPayout({
        registered: true,
        contact_id: data.contact_id,
        fund_account_id: data.fund_account_id,
      });
      setSuccess("Bank account linked for RazorpayX payouts.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmittingBank(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card page-card">
          <p>Please <Link href="/login">sign in</Link> as a tasker to complete KYC and payout setup.</p>
        </div>
      </main>
    );
  }

  if (!isTasker) {
    return (
      <main className="page-shell">
        <div className="glass-card page-card">
          <p>KYC and payout onboarding is for <b>taskers</b> only. Posters manage payments on the <Link href="/payments">Payments</Link> page.</p>
        </div>
      </main>
    );
  }

  const kycStatus = (kyc?.status || "none").toLowerCase();
  const kycMeta = KYC_STATUS[kycStatus] || KYC_STATUS.none;
  const KycIcon = kycMeta.icon;
  const canRegisterBank = kycStatus === "verified" && !payout?.registered;
  const showKycForm = kycStatus === "none" || kycStatus === "rejected";

  return (
    <main className="page-shell">
      <header className="page-header">
        <h1><ShieldCheck size={28} /> KYC & Payout Setup</h1>
        <p>Verify your identity, then link a bank account to receive escrow payouts via RazorpayX.</p>
      </header>

      {error && <div className="banner error"><AlertTriangle size={16} /> {error}</div>}
      {success && <div className="banner success"><CheckCircle2 size={16} /> {success}</div>}

      {loading ? (
        <div className="glass-card empty"><Loader className="spin" size={22} /> Loading…</div>
      ) : (
        <>
          <div className="glass-card section-card">
            <h2>Step 1 — Identity (KYC)</h2>
            <div className="status-row" style={{ borderColor: kycMeta.color }}>
              <KycIcon size={20} style={{ color: kycMeta.color }} />
              <div>
                <strong style={{ color: kycMeta.color }}>{kycMeta.label}</strong>
                {kyc?.pan_masked && <p className="meta">PAN {kyc.pan_masked}{kyc.aadhaar_last4 ? ` · Aadhaar ••••${kyc.aadhaar_last4}` : ""}</p>}
                {kyc?.rejection_reason && <p className="meta reject">{kyc.rejection_reason}</p>}
              </div>
            </div>

            {showKycForm ? (
              <form onSubmit={handleKycSubmit} className="form-grid">
                <label>
                  Full name (as on PAN)
                  <input
                    required
                    value={kycForm.full_name}
                    onChange={(e) => setKycForm((f) => ({ ...f, full_name: e.target.value }))}
                    placeholder="Rahul Sharma"
                  />
                </label>
                <label>
                  PAN (10 characters)
                  <input
                    required
                    maxLength={10}
                    value={kycForm.pan}
                    onChange={(e) => setKycForm((f) => ({ ...f, pan: e.target.value.toUpperCase() }))}
                    placeholder="ABCDE1234F"
                  />
                </label>
                <label>
                  Aadhaar last 4 digits (optional)
                  <input
                    maxLength={4}
                    inputMode="numeric"
                    value={kycForm.aadhaar_last4}
                    onChange={(e) => setKycForm((f) => ({ ...f, aadhaar_last4: e.target.value.replace(/\D/g, "") }))}
                    placeholder="1234"
                  />
                </label>
                <button type="submit" className="btn-premium btn-teal" disabled={submittingKyc}>
                  {submittingKyc ? "Submitting…" : "Submit KYC"}
                </button>
              </form>
            ) : kycStatus === "pending" ? (
              <p className="hint">Your submission is pending review. In dev, set <code>KYC_STUB_AUTO_VERIFY=true</code> for instant approval.</p>
            ) : (
              <p className="hint verified">Identity verified{kyc?.verified_at ? ` on ${new Date(kyc.verified_at).toLocaleDateString()}` : ""}.</p>
            )}
          </div>

          <div className="glass-card section-card">
            <h2><Banknote size={18} /> Step 2 — Bank account (RazorpayX)</h2>
            {payout?.registered ? (
              <div className="status-row" style={{ borderColor: "#10b981" }}>
                <CheckCircle2 size={20} style={{ color: "#10b981" }} />
                <div>
                  <strong style={{ color: "#10b981" }}>Payout account linked</strong>
                  <p className="meta">Fund account: <code>{payout.fund_account_id}</code></p>
                </div>
              </div>
            ) : kycStatus !== "verified" ? (
              <p className="hint">Complete KYC verification before linking your bank account.</p>
            ) : (
              <form onSubmit={handleBankSubmit} className="form-grid">
                <label>
                  Beneficiary name
                  <input
                    required
                    value={bankForm.beneficiary_name}
                    onChange={(e) => setBankForm((f) => ({ ...f, beneficiary_name: e.target.value }))}
                    placeholder="Account holder name"
                  />
                </label>
                <label>
                  IFSC code
                  <input
                    required
                    maxLength={11}
                    value={bankForm.ifsc}
                    onChange={(e) => setBankForm((f) => ({ ...f, ifsc: e.target.value.toUpperCase() }))}
                    placeholder="HDFC0001234"
                  />
                </label>
                <label>
                  Account number
                  <input
                    required
                    inputMode="numeric"
                    value={bankForm.account_number}
                    onChange={(e) => setBankForm((f) => ({ ...f, account_number: e.target.value.replace(/\D/g, "") }))}
                    placeholder="9–18 digits"
                  />
                </label>
                <button type="submit" className="btn-premium btn-saffron" disabled={submittingBank || !canRegisterBank}>
                  {submittingBank ? "Registering…" : "Link bank for payouts"}
                </button>
                <p className="hint">Requires Razorpay test keys and RazorpayX payout account in backend <code>.env</code>.</p>
              </form>
            )}
          </div>
        </>
      )}

      <style jsx>{`
        .page-shell { max-width: 680px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .page-header h1 { display: flex; align-items: center; gap: 10px; font-size: 1.75rem; font-weight: 800; }
        .page-header p { color: var(--color-text-muted); margin-top: 8px; font-size: 0.9rem; }
        .banner { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-radius: 10px; font-size: 0.85rem; }
        .banner.error { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
        .banner.success { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25); color: #6ee7b7; }
        .section-card { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
        .section-card h2 { font-size: 1rem; font-weight: 700; display: flex; align-items: center; gap: 8px; border-left: 3px solid var(--color-teal); padding-left: 10px; }
        .status-row { display: flex; gap: 12px; align-items: flex-start; padding: 14px; border-radius: 10px; border: 1px solid; background: rgba(255,255,255,0.02); }
        .meta { font-size: 0.78rem; color: var(--color-text-muted); margin-top: 4px; }
        .meta.reject { color: #fca5a5; }
        .meta code { color: var(--color-teal); font-size: 0.72rem; }
        .hint { font-size: 0.82rem; color: var(--color-text-muted); line-height: 1.5; }
        .hint code { color: var(--color-teal); font-size: 0.78rem; }
        .hint.verified { color: #6ee7b7; }
        .form-grid { display: flex; flex-direction: column; gap: 14px; margin-top: 8px; }
        label { display: flex; flex-direction: column; gap: 6px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--color-text-muted); }
        input {
          background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px;
          padding: 11px 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.9rem; outline: none;
        }
        input:focus { border-color: var(--color-teal); }
        .empty { padding: 32px; display: flex; align-items: center; gap: 10px; color: var(--color-text-muted); }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

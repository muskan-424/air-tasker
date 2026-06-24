"use client";

import React, { useState } from "react";
import { useBeta } from "@/context/BetaContext";
import { useAuth } from "@/context/AuthContext";
import { betaAPI } from "@/lib/api";
import { MessageSquare, Send, CheckCircle2, AlertTriangle } from "lucide-react";

export default function FeedbackPage() {
  const { config } = useBeta();
  const { user, isLoggedIn } = useAuth();
  const [category, setCategory] = useState("support");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await betaAPI.submitFeedback({
        category,
        message,
        email: email || user?.email || null,
        page_path: typeof window !== "undefined" ? window.location.pathname : null,
      });
      setDone(true);
      setMessage("");
    } catch (err) {
      setError(err.message || "Could not submit feedback");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feedback-wrapper">
      <div className="feedback-header glass-card">
        <MessageSquare style={{ width: 28, height: 28, color: "var(--color-teal)" }} />
        <div>
          <h1>Beta feedback</h1>
          <p>
            Help us improve VayuTask during the closed beta in{" "}
            {config.city_label || "your city cluster"}.
          </p>
        </div>
      </div>

      {done && (
        <div className="feedback-success glass-card">
          <CheckCircle2 style={{ width: 20, height: 20, color: "#10b981" }} />
          Thank you — your feedback was received. Our team will review it during the beta window.
        </div>
      )}

      {error && (
        <div className="api-error-bar">
          <AlertTriangle style={{ width: 16, height: 16 }} /> {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="feedback-form glass-card">
        <label>
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="support">Support / help</option>
            <option value="bug">Bug report</option>
            <option value="feature">Feature idea</option>
            <option value="other">Other</option>
          </select>
        </label>

        {!isLoggedIn && (
          <label>
            Email (optional)
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
        )}

        <label>
          Message
          <textarea
            required
            minLength={5}
            rows={6}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe what happened, which page, and your PIN/category if relevant..."
          />
        </label>

        <button type="submit" className="btn-premium btn-teal" disabled={loading}>
          <Send style={{ width: 16, height: 16 }} />
          {loading ? "Sending..." : "Submit feedback"}
        </button>
      </form>

      <div className="feedback-playbook glass-card">
        <h3>Support playbook (beta)</h3>
        <ul>
          <li>Task not visible on radar? Confirm PIN is in beta cluster: {config.pin_codes?.join(", ")}.</li>
          <li>Publish blocked? Use categories: {config.categories?.join(", ")}.</li>
          <li>Payments/KYC issues? Include task ID and screenshot in your message.</li>
          <li>Sev-1 (payments down): email ops immediately; do not retry checkout repeatedly.</li>
        </ul>
        <p className="muted">Full runbook: repo <code>beta/SUPPORT_PLAYBOOK.md</code></p>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .feedback-wrapper { display: flex; flex-direction: column; gap: 20px; max-width: 720px; margin: 0 auto; }
        .feedback-header { display: flex; gap: 16px; align-items: flex-start; padding: 24px; }
        .feedback-header h1 { margin: 0 0 6px; font-size: 1.6rem; }
        .feedback-form, .feedback-playbook, .feedback-success { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
        .feedback-form label { display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem; font-weight: 600; }
        .feedback-form input, .feedback-form select, .feedback-form textarea {
          padding: 12px; border-radius: 10px; border: 1px solid var(--border-glow);
          background: rgba(255,255,255,0.03); color: inherit;
        }
        .feedback-success { display: flex; align-items: center; gap: 10px; color: #10b981; }
        .feedback-playbook ul { margin: 0; padding-left: 20px; color: var(--color-text-muted); }
        .feedback-playbook .muted { font-size: 0.85rem; color: var(--color-text-muted); }
      ` }} />
    </div>
  );
}

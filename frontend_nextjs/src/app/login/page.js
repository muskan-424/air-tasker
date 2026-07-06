"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, LogIn, UserPlus, Mail, Lock, Shield } from "lucide-react";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [tab, setTab] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("POSTER");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (tab === "login") {
        await login(email, password);
      } else {
        await register(email, password, role);
      }
      window.location.href = "/";
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-card glass-card">
        {/* Header */}
        <div className="login-header">
          <div className="logo-row">
            <span className="logo-dot"></span>
            <span className="logo-text">VayuTask <span className="logo-ai">AI</span></span>
          </div>
          <h1>Welcome Back</h1>
          <p>India's AI-Native Gig Marketplace. Sign in to continue.</p>
        </div>

        {/* Tab switcher */}
        <div className="tab-switcher">
          <button
            onClick={() => { setTab("login"); setError(null); }}
            className={`tab-btn ${tab === "login" ? "tab-active" : ""}`}
          >
            <LogIn className="tab-icon" /> Sign In
          </button>
          <button
            onClick={() => { setTab("register"); setError(null); }}
            className={`tab-btn ${tab === "register" ? "tab-active" : ""}`}
          >
            <UserPlus className="tab-icon" /> Register
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form">
          {/* Email */}
          <div className="field-group">
            <label htmlFor="email">Email Address</label>
            <div className="input-row">
              <Mail className="input-icon" />
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          {/* Password */}
          <div className="field-group">
            <label htmlFor="password">Password</label>
            <div className="input-row">
              <Lock className="input-icon" />
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={tab === "login" ? "current-password" : "new-password"}
              />
            </div>
          </div>

          {/* Role selector — only for registration */}
          {tab === "register" && (
            <div className="field-group">
              <label>I am a...</label>
              <div className="role-selector">
                {["POSTER", "TASKER"].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`role-option ${role === r ? "role-active" : ""}`}
                  >
                    <Shield className="role-icon" />
                    <span>{r === "POSTER" ? "Poster (I need tasks done)" : "Tasker (I do the work)"}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="error-alert">
              <span>⚠ {error}</span>
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="btn-premium btn-teal submit-btn"
          >
            {loading ? (
              <span className="loading-dots">Processing<span>.</span><span>.</span><span>.</span></span>
            ) : (
              <>
                <Sparkles className="btn-icon" />
                {tab === "login" ? "Sign In" : "Create Account"}
              </>
            )}
          </button>
        </form>

      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .login-wrapper {
          min-height: 80vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 40px 24px;
        }
        .login-card {
          width: 100%;
          max-width: 440px;
          padding: 40px;
          display: flex;
          flex-direction: column;
          gap: 28px;
        }
        .login-header {
          text-align: center;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .logo-row {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        .logo-dot {
          width: 10px;
          height: 10px;
          background: var(--color-teal);
          border-radius: 50%;
          box-shadow: 0 0 8px var(--color-teal);
        }
        .logo-text {
          font-family: var(--font-heading);
          font-size: 1.3rem;
          font-weight: 800;
        }
        .logo-ai {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 5px;
          background: linear-gradient(135deg, var(--color-teal) 0%, #0d9488 100%);
          color: #042f2e;
          font-weight: 700;
          vertical-align: middle;
          margin-left: 2px;
        }
        .login-header h1 {
          font-size: 1.6rem;
          font-weight: 800;
          color: var(--color-text-main);
        }
        .login-header p {
          font-size: 0.85rem;
          color: var(--color-text-muted);
        }

        .tab-switcher {
          display: flex;
          background: rgba(255,255,255,0.02);
          border: 1px solid var(--border-glow);
          border-radius: 12px;
          padding: 4px;
          gap: 4px;
        }
        .tab-btn {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 10px;
          border-radius: 8px;
          background: transparent;
          border: none;
          color: var(--color-text-muted);
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.2s ease;
          font-family: inherit;
        }
        .tab-active {
          background: rgba(20, 184, 166, 0.1);
          color: var(--color-teal);
          border: 1px solid var(--border-teal);
        }
        .tab-icon {
          width: 16px;
          height: 16px;
        }

        .login-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .field-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .field-group label {
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--color-text-muted);
        }
        .input-row {
          display: flex;
          align-items: center;
          background: rgba(7, 9, 19, 0.6);
          border: 1px solid var(--border-glow);
          border-radius: 10px;
          padding: 4px 14px;
          gap: 10px;
          transition: border-color 0.2s ease;
        }
        .input-row:focus-within {
          border-color: var(--color-teal);
        }
        .input-icon {
          color: var(--color-text-muted);
          width: 18px;
          height: 18px;
          flex-shrink: 0;
        }
        .input-row input {
          flex: 1;
          background: transparent;
          border: none;
          color: var(--color-text-main);
          font-family: inherit;
          font-size: 0.95rem;
          padding: 10px 0;
          outline: none;
        }
        .input-row input::placeholder {
          color: rgba(148, 163, 184, 0.5);
        }

        .role-selector {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .role-option {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 16px;
          background: rgba(7, 9, 19, 0.4);
          border: 1px solid var(--border-glow);
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s ease;
          font-family: inherit;
          font-size: 0.9rem;
          color: var(--color-text-muted);
          text-align: left;
        }
        .role-option:hover {
          border-color: rgba(20, 184, 166, 0.3);
          color: var(--color-text-main);
        }
        .role-active {
          border-color: var(--color-teal) !important;
          background: rgba(20, 184, 166, 0.05) !important;
          color: var(--color-teal) !important;
        }
        .role-icon {
          width: 18px;
          height: 18px;
          flex-shrink: 0;
        }

        .error-alert {
          padding: 12px 16px;
          background: rgba(239, 68, 68, 0.08);
          border: 1px solid rgba(239, 68, 68, 0.25);
          border-radius: 10px;
          color: #fca5a5;
          font-size: 0.85rem;
          font-weight: 500;
        }

        .submit-btn {
          width: 100%;
          padding: 14px;
          font-size: 1rem;
        }

        .loading-dots span {
          animation: blink 1.2s infinite;
        }
        .loading-dots span:nth-child(2) { animation-delay: 0.2s; }
        .loading-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink {
          0%, 80%, 100% { opacity: 0; }
          40% { opacity: 1; }
        }

        .backend-note {
          text-align: center;
          font-size: 0.75rem;
          color: var(--color-text-muted);
          line-height: 1.4;
        }
        .backend-note code {
          background: rgba(255,255,255,0.06);
          padding: 2px 5px;
          border-radius: 4px;
          font-size: 0.7rem;
        }
      ` }} />
    </div>
  );
}

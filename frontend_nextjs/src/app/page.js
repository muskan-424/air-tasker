"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";

// ── Animated counter hook ────────────────────────────────────────────────────
function useCounter(target, duration = 2000, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime = null;
    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [start, target, duration]);
  return count;
}

const FEATURES = [
  {
    id: "poster",
    route: "/poster",
    label: "Post tasks",
    title: "AI Task Generator",
    tagline: "Speak. AI does the rest.",
    desc: "Describe your task in any Indian language — Hindi, Tamil, Marathi — and AI structures it into a clear contract with tools, budget, and evidence needs.",
    badge: "AI Draft",
    accent: "teal",
    icon: "🎙️",
    stats: "< 3s",
    statsLabel: "to draft",
  },
  {
    id: "tasker",
    route: "/tasker",
    label: "Find work",
    title: "Tasker Radar",
    tagline: "Find work near you instantly.",
    desc: "Live radar feed of tasks around your PIN code. Accept a gig, acknowledge the checklist, and get routed directly to the payment escrow flow.",
    badge: "Location Match",
    accent: "saffron",
    icon: "📡",
    stats: "Live",
    statsLabel: "feed",
  },
  {
    id: "chat",
    route: "/chat",
    label: "Chat",
    title: "Translated Chat",
    tagline: "Speak your language, they understand theirs.",
    desc: "Real-time bilingual chat. Every message is translated inline — poster and tasker never need to share a language.",
    badge: "Live Translate",
    accent: "teal",
    icon: "💬",
    stats: "22+",
    statsLabel: "languages",
  },
  {
    id: "verify",
    route: "/verify",
    label: "Verify work",
    title: "Photo Verification",
    tagline: "See the difference. Release the money.",
    desc: "Upload before/after photos. AI checks the evidence and unlocks escrow when the job looks complete.",
    badge: "Photo Verify",
    accent: "purple",
    icon: "👁️",
    stats: "92%",
    statsLabel: "accuracy",
  },
  {
    id: "payments",
    route: "/payments",
    label: "Pay securely",
    title: "Secure Escrow",
    tagline: "Money moves only when work is done.",
    desc: "Funds are locked when work starts, held securely, and released to the tasker only after verification passes.",
    badge: "RazorpayX",
    accent: "gold",
    icon: "🔐",
    stats: "₹0",
    statsLabel: "dispute risk",
  },
];

const STEPS = [
  { num: "01", title: "Post Your Task", desc: "Speak or type in any language. AI generates a structured contract.", icon: "✍️" },
  { num: "02", title: "Tasker Accepts", desc: "A nearby verified tasker spots it on the radar and accepts.", icon: "🤝" },
  { num: "03", title: "Escrow Locks", desc: "Payment is held securely in Razorpay escrow — zero risk.", icon: "🔒" },
  { num: "04", title: "Work & Verify", desc: "Tasker submits photo proof. AI verifies before/after evidence.", icon: "✅" },
  { num: "05", title: "Get Paid", desc: "Funds release instantly to the tasker via RazorpayX payout.", icon: "💸" },
];

export default function Home() {
  const { isLoggedIn, user } = useAuth();
  const [statsVisible, setStatsVisible] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const statsRef = useRef(null);

  const tasksCount = useCounter(12480, 1800, statsVisible);
  const taskersCount = useCounter(4200, 1600, statsVisible);
  const escrowCount = useCounter(98, 1400, statsVisible);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStatsVisible(true); },
      { threshold: 0.3 }
    );
    if (statsRef.current) observer.observe(statsRef.current);
    return () => observer.disconnect();
  }, []);

  const accentStyles = {
    teal: { color: "var(--color-teal)", border: "var(--border-teal)", bg: "rgba(20,184,166,0.07)", badge: "rgba(20,184,166,0.1)" },
    saffron: { color: "var(--color-saffron)", border: "var(--border-saffron)", bg: "rgba(245,158,11,0.07)", badge: "rgba(245,158,11,0.1)" },
    purple: { color: "#a78bfa", border: "rgba(167,139,250,0.25)", bg: "rgba(167,139,250,0.07)", badge: "rgba(167,139,250,0.1)" },
    gold: { color: "#f59e0b", border: "rgba(245,158,11,0.3)", bg: "rgba(245,158,11,0.07)", badge: "rgba(251,191,36,0.1)" },
  };

  return (
    <div className="home-page">

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section className="hero-section">
        {/* Glow orbs */}
        <div className="orb orb-teal"></div>
        <div className="orb orb-saffron"></div>

        <div className="hero-eyebrow">
          <span className="eyebrow-dot"></span>
          <span>Now Live in Beta · India's First AI-Native Gig Marketplace</span>
        </div>

        <h1 className="hero-title">
          Any Task.<br />
          <span className="hero-gradient">Any Language.</span><br />
          Zero Friction.
        </h1>

        <p className="hero-subtitle">
          Post gigs in Hindi, Tamil, or Marathi. AI builds the contract,
          live translation bridges languages, and Razorpay escrow protects your payment.
          The smartest way to get things done in India.
        </p>

        <div className="hero-cta-row">
          {isLoggedIn ? (
            <>
              <a href="/poster" className="btn-premium btn-teal cta-primary">
                🎙️ Post a Task
              </a>
              <a href="/tasker" className="btn-premium btn-saffron cta-secondary">
                📡 Find Work
              </a>
            </>
          ) : (
            <>
              <a href="/login" className="btn-premium btn-teal cta-primary">
                Get Started Free →
              </a>
              <a href="/poster" className="btn-premium btn-outline cta-secondary">
                See How It Works
              </a>
            </>
          )}
        </div>

        {isLoggedIn && user && (
          <div className="welcome-back-chip">
            <span className="wb-dot"></span>
            Welcome back, <strong>{user.email?.split("@")[0]}</strong> · {user.role || "User"}
          </div>
        )}

        {/* Tech stack pills */}
        <div className="tech-pills">
          {["AI drafts", "Voice input", "Live chat", "Secure escrow", "Photo verify", "Local taskers"].map((t) => (
            <span key={t} className="tech-pill">{t}</span>
          ))}
        </div>
      </section>

      {/* ── STATS ────────────────────────────────────────────────────────── */}
      <section ref={statsRef} className="stats-section glass-card">
        <div className="stat-item">
          <div className="stat-number">{tasksCount.toLocaleString()}+</div>
          <div className="stat-label">Tasks Posted</div>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <div className="stat-number">{taskersCount.toLocaleString()}+</div>
          <div className="stat-label">Active Taskers</div>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <div className="stat-number">{escrowCount}%</div>
          <div className="stat-label">Escrow Success Rate</div>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <div className="stat-number">22+</div>
          <div className="stat-label">Indian Languages</div>
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────────── */}
      <section className="features-section">
        <div className="section-header">
          <div className="section-eyebrow">Platform Features</div>
          <h2 className="section-title">Every Part of the Gig Lifecycle, Reimagined</h2>
          <p className="section-subtitle">Five AI-native modules working together as one seamless platform.</p>
        </div>

        <div className="features-grid">
          {FEATURES.map((f) => {
            const s = accentStyles[f.accent];
            const isHovered = hoveredFeature === f.id;
            return (
              <div
                key={f.id}
                className="feature-card glass-card"
                style={{
                  borderColor: isHovered ? s.color : undefined,
                  background: isHovered ? s.bg : undefined,
                  boxShadow: isHovered ? `0 0 40px ${s.bg}` : undefined,
                }}
                onMouseEnter={() => setHoveredFeature(f.id)}
                onMouseLeave={() => setHoveredFeature(null)}
              >
                {/* Top row */}
                <div className="fc-top">
                  <div className="fc-icon-box" style={{ background: s.badge, borderColor: s.border }}>
                    <span className="fc-icon">{f.icon}</span>
                  </div>
                  <div className="fc-meta">
                    <span className="fc-label" style={{ color: s.color }}>{f.label}</span>
                    <span className="fc-badge" style={{ background: s.badge, color: s.color, borderColor: s.border }}>{f.badge}</span>
                  </div>
                </div>

                {/* Stat */}
                <div className="fc-stat" style={{ color: s.color }}>
                  <span className="fc-stat-number">{f.stats}</span>
                  <span className="fc-stat-label">{f.statsLabel}</span>
                </div>

                {/* Text */}
                <div className="fc-body">
                  <h3 className="fc-title">{f.title}</h3>
                  <p className="fc-tagline" style={{ color: s.color }}>{f.tagline}</p>
                  <p className="fc-desc">{f.desc}</p>
                </div>

                {/* CTA */}
                <a
                  href={f.route}
                  className="fc-cta btn-premium"
                  style={{
                    background: `linear-gradient(135deg, ${s.color}, ${s.color}cc)`,
                    color: f.accent === "teal" ? "#042f2e" : f.accent === "purple" ? "#1e1b4b" : "#3b1500",
                    border: "none",
                  }}
                >
                  Open {f.title} →
                </a>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
      <section className="how-section">
        <div className="section-header">
          <div className="section-eyebrow">How It Works</div>
          <h2 className="section-title">From Request to Payout in 5 Steps</h2>
        </div>

        <div className="steps-row">
          {STEPS.map((step, idx) => (
            <React.Fragment key={step.num}>
              <div className="step-card glass-card">
                <div className="step-num-row">
                  <span className="step-icon">{step.icon}</span>
                  <span className="step-num">{step.num}</span>
                </div>
                <h4 className="step-title">{step.title}</h4>
                <p className="step-desc">{step.desc}</p>
              </div>
              {idx < STEPS.length - 1 && (
                <div className="step-arrow">→</div>
              )}
            </React.Fragment>
          ))}
        </div>
      </section>

      {/* ── FINAL CTA ────────────────────────────────────────────────────── */}
      <section className="final-cta-section glass-card">
        <div className="fta-orb"></div>
        <div className="fta-content">
          <h2 className="fta-title">
            Ready to experience India's most intelligent gig platform?
          </h2>
          <p className="fta-subtitle">
            Register in seconds. No fees. No friction. Just AI-powered work done right.
          </p>
          <div className="fta-btns">
            <a href="/login" className="btn-premium btn-teal fta-btn">
              Start for Free →
            </a>
            <a href="/chat" className="btn-premium btn-outline fta-btn">
              Try AI Chat
            </a>
          </div>
          <p className="fta-note">Secure payments · Multilingual · AI-powered</p>
        </div>
      </section>

      {/* ── STYLES ───────────────────────────────────────────────────────── */}
      <style dangerouslySetInnerHTML={{ __html: `
        .home-page {
          display: flex;
          flex-direction: column;
          gap: 80px;
          padding-bottom: 40px;
        }

        /* ── Hero ── */
        .hero-section {
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 28px;
          padding: 60px 24px 20px;
          position: relative;
          overflow: hidden;
        }
        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.25;
          pointer-events: none;
        }
        .orb-teal {
          width: 500px; height: 500px;
          background: var(--color-teal);
          top: -200px; left: 50%;
          transform: translateX(-50%);
        }
        .orb-saffron {
          width: 300px; height: 300px;
          background: var(--color-saffron);
          bottom: -80px; right: 10%;
          opacity: 0.12;
        }

        .hero-eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--color-teal);
          background: rgba(20,184,166,0.07);
          border: 1px solid var(--border-teal);
          padding: 6px 16px;
          border-radius: 20px;
        }
        .eyebrow-dot {
          width: 7px; height: 7px;
          border-radius: 50%;
          background: var(--color-teal);
          box-shadow: 0 0 8px var(--color-teal);
          animation: pulse-glow-teal 2s infinite;
        }

        .hero-title {
          font-size: clamp(2.8rem, 7vw, 5rem);
          font-weight: 900;
          line-height: 1.1;
          letter-spacing: -0.04em;
          color: var(--color-text-main);
          position: relative;
          z-index: 1;
        }
        .hero-gradient {
          background: linear-gradient(135deg, var(--color-teal) 0%, #0d9488 40%, var(--color-saffron) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .hero-subtitle {
          font-size: 1.15rem;
          color: var(--color-text-muted);
          max-width: 680px;
          line-height: 1.7;
          position: relative;
          z-index: 1;
        }

        .hero-cta-row {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          justify-content: center;
          position: relative;
          z-index: 1;
        }
        .cta-primary { padding: 16px 36px; font-size: 1.05rem; }
        .cta-secondary { padding: 16px 28px; font-size: 1rem; }

        .welcome-back-chip {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 8px 18px;
          border-radius: 20px;
          background: rgba(20,184,166,0.06);
          border: 1px solid var(--border-teal);
          font-size: 0.85rem;
          color: var(--color-text-muted);
          z-index: 1;
        }
        .wb-dot {
          width: 8px; height: 8px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 6px #10b981;
        }
        .welcome-back-chip strong { color: var(--color-text-main); }

        .tech-pills {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          justify-content: center;
          z-index: 1;
        }
        .tech-pill {
          padding: 5px 14px;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 600;
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border-glow);
          color: var(--color-text-muted);
          letter-spacing: 0.02em;
        }

        /* ── Stats ── */
        .stats-section {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0;
          padding: 36px 40px;
          flex-wrap: wrap;
        }
        .stat-item {
          flex: 1;
          min-width: 140px;
          text-align: center;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .stat-number {
          font-size: 2.4rem;
          font-weight: 900;
          letter-spacing: -0.03em;
          background: linear-gradient(135deg, var(--color-teal), var(--color-saffron));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .stat-label {
          font-size: 0.8rem;
          font-weight: 600;
          color: var(--color-text-muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }
        .stat-divider {
          width: 1px;
          height: 50px;
          background: var(--border-glow);
          margin: 0 20px;
        }

        /* ── Features ── */
        .features-section {
          display: flex;
          flex-direction: column;
          gap: 48px;
        }
        .section-header {
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 14px;
        }
        .section-eyebrow {
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--color-teal);
          background: rgba(20,184,166,0.07);
          border: 1px solid var(--border-teal);
          padding: 5px 14px;
          border-radius: 20px;
        }
        .section-title {
          font-size: clamp(1.8rem, 4vw, 2.8rem);
          font-weight: 800;
          max-width: 700px;
        }
        .section-subtitle {
          color: var(--color-text-muted);
          font-size: 1rem;
          max-width: 550px;
        }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 24px;
        }
        .feature-card {
          padding: 28px;
          display: flex;
          flex-direction: column;
          gap: 18px;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        .fc-top {
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .fc-icon-box {
          width: 52px; height: 52px;
          border-radius: 14px;
          border-width: 1px;
          border-style: solid;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .fc-icon { font-size: 1.6rem; }
        .fc-meta {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }
        .fc-label {
          font-size: 0.7rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
        .fc-badge {
          font-size: 0.65rem;
          font-weight: 700;
          padding: 3px 8px;
          border-radius: 8px;
          border-width: 1px;
          border-style: solid;
          display: inline-block;
        }
        .fc-stat {
          display: flex;
          align-items: baseline;
          gap: 6px;
        }
        .fc-stat-number {
          font-size: 2rem;
          font-weight: 900;
          letter-spacing: -0.03em;
        }
        .fc-stat-label {
          font-size: 0.8rem;
          color: var(--color-text-muted);
        }
        .fc-body {
          display: flex;
          flex-direction: column;
          gap: 8px;
          flex: 1;
        }
        .fc-title {
          font-size: 1.3rem;
          font-weight: 800;
          color: var(--color-text-main);
        }
        .fc-tagline {
          font-size: 0.88rem;
          font-weight: 600;
          font-style: italic;
        }
        .fc-desc {
          font-size: 0.88rem;
          color: var(--color-text-muted);
          line-height: 1.55;
        }
        .fc-cta {
          width: 100%;
          padding: 12px;
          border-radius: 10px;
          font-size: 0.9rem;
          font-weight: 700;
          text-align: center;
          transition: all 0.2s ease;
          opacity: 0.9;
        }
        .fc-cta:hover { opacity: 1; transform: translateY(-1px); }

        /* ── How It Works ── */
        .how-section {
          display: flex;
          flex-direction: column;
          gap: 48px;
        }
        .steps-row {
          display: flex;
          align-items: stretch;
          gap: 0;
          overflow-x: auto;
          padding-bottom: 8px;
        }
        .step-card {
          flex: 1;
          min-width: 170px;
          padding: 24px 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          border-radius: 14px;
        }
        .step-num-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .step-icon { font-size: 1.6rem; }
        .step-num {
          font-size: 0.7rem;
          font-weight: 800;
          color: var(--color-text-muted);
          letter-spacing: 0.05em;
          background: rgba(255,255,255,0.04);
          padding: 3px 8px;
          border-radius: 6px;
        }
        .step-title {
          font-size: 1rem;
          font-weight: 700;
        }
        .step-desc {
          font-size: 0.82rem;
          color: var(--color-text-muted);
          line-height: 1.5;
          flex: 1;
        }
        .step-arrow {
          display: flex;
          align-items: center;
          padding: 0 8px;
          font-size: 1.4rem;
          color: var(--color-teal);
          opacity: 0.5;
          flex-shrink: 0;
        }

        /* ── Final CTA ── */
        .final-cta-section {
          padding: 60px 48px;
          text-align: center;
          position: relative;
          overflow: hidden;
          border-color: var(--border-teal);
        }
        .fta-orb {
          position: absolute;
          width: 400px; height: 400px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(20,184,166,0.15) 0%, transparent 70%);
          top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          pointer-events: none;
        }
        .fta-content {
          position: relative;
          z-index: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
        }
        .fta-title {
          font-size: clamp(1.6rem, 3.5vw, 2.4rem);
          font-weight: 800;
          max-width: 680px;
          line-height: 1.2;
        }
        .fta-subtitle {
          font-size: 1rem;
          color: var(--color-text-muted);
          max-width: 500px;
        }
        .fta-btns {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          justify-content: center;
        }
        .fta-btn { padding: 14px 32px; font-size: 1rem; }
        .fta-note {
          font-size: 0.75rem;
          color: var(--color-text-muted);
          margin-top: 4px;
        }

        /* ── Responsive ── */
        @media (max-width: 768px) {
          .hero-section { padding: 40px 16px 0; }
          .stats-section { gap: 24px; flex-direction: column; }
          .stat-divider { display: none; }
          .features-grid { grid-template-columns: 1fr; }
          .steps-row { flex-direction: column; }
          .step-arrow { transform: rotate(90deg); align-self: center; }
          .final-cta-section { padding: 40px 24px; }
        }
      ` }} />
    </div>
  );
}

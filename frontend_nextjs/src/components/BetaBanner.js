"use client";

import Link from "next/link";
import { useBeta } from "@/context/BetaContext";

export default function BetaBanner() {
  const { config, loading } = useBeta();
  if (loading || !config.beta_enabled) return null;

  const langs = (config.languages || []).map((l) => l.label).join(" · ");
  const cats = (config.categories || []).join(", ");

  return (
    <div className="beta-banner">
      <div className="beta-banner-inner">
        <strong>Closed beta</strong>
        <span>
          {config.city_label} · Categories: {cats} · Languages: {langs}
        </span>
        <Link href={config.feedback_path || "/feedback"} className="beta-feedback-link">
          Send feedback
        </Link>
      </div>
      <style dangerouslySetInnerHTML={{ __html: `
        .beta-banner {
          background: linear-gradient(90deg, rgba(20,184,166,0.12), rgba(245,158,11,0.08));
          border-bottom: 1px solid rgba(20,184,166,0.25);
        }
        .beta-banner-inner {
          max-width: 1200px;
          margin: 0 auto;
          padding: 10px 24px;
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          align-items: center;
          justify-content: center;
          font-size: 0.85rem;
          color: var(--color-text-muted);
        }
        .beta-banner-inner strong { color: var(--color-teal); }
        .beta-feedback-link {
          color: var(--color-saffron);
          font-weight: 600;
          text-decoration: underline;
        }
      ` }} />
    </div>
  );
}

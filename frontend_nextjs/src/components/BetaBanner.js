"use client";

import Link from "next/link";
import { useBeta } from "@/context/BetaContext";

export default function BetaBanner() {
  const { config, loading } = useBeta();
  if (loading || !config.beta_enabled) return null;

  return (
    <div className="beta-banner">
      <div className="beta-banner-inner">
        <span className="beta-tag">Beta</span>
        {config.city_label && <span className="beta-cities">{config.city_label}</span>}
        <Link href={config.feedback_path || "/feedback"} className="beta-feedback-link">
          Send feedback
        </Link>
      </div>
      <style dangerouslySetInnerHTML={{ __html: `
        .beta-banner-inner {
          max-width: 1200px;
          margin: 0 auto;
          padding: 6px 24px 0;
          display: flex;
          gap: 10px;
          align-items: center;
          justify-content: flex-end;
          font-size: 0.75rem;
          color: var(--color-text-muted);
        }
        .beta-tag {
          padding: 1px 8px;
          border-radius: 999px;
          border: 1px solid rgba(20,184,166,0.4);
          color: var(--color-teal);
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          font-size: 0.68rem;
        }
        .beta-cities { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .beta-feedback-link {
          color: var(--color-text-muted);
          text-decoration: underline;
          white-space: nowrap;
        }
        .beta-feedback-link:hover { color: var(--color-teal); }
      ` }} />
    </div>
  );
}

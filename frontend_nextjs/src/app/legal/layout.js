"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle } from "lucide-react";

const PAGES = [
  { href: "/legal/terms", label: "Terms of Service" },
  { href: "/legal/privacy", label: "Privacy Policy" },
  { href: "/legal/community-guidelines", label: "Community Guidelines" },
  { href: "/legal/cancellation-policy", label: "Cancellation Policy" },
];

export default function LegalLayout({ children }) {
  const pathname = usePathname();
  return (
    <main className="legal-shell">
      <div className="draft-banner">
        <AlertTriangle size={16} />
        <span>
          Draft for review, not legal advice. Have a lawyer review these pages — especially the Privacy
          Policy against India&apos;s DPDP Act 2023 — before this goes live for real users.
        </span>
      </div>

      <div className="legal-layout">
        <nav className="legal-nav">
          {PAGES.map((p) => (
            <Link key={p.href} href={p.href} className={pathname === p.href ? "active" : ""}>
              {p.label}
            </Link>
          ))}
        </nav>
        <article className="legal-content glass-card">{children}</article>
      </div>

      <style jsx>{`
        .legal-shell { max-width: 1000px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .draft-banner {
          display: flex; align-items: flex-start; gap: 10px; padding: 12px 16px; border-radius: 10px;
          background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: var(--color-saffron);
          font-size: 0.82rem; line-height: 1.5;
        }
        .legal-layout { display: grid; grid-template-columns: 200px 1fr; gap: 24px; align-items: start; }
        .legal-nav { display: flex; flex-direction: column; gap: 4px; position: sticky; top: 24px; }
        .legal-nav a {
          padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; color: var(--color-text-muted);
          text-decoration: none; transition: all 0.15s ease;
        }
        .legal-nav a:hover { color: var(--color-text-main); background: rgba(255,255,255,0.04); }
        .legal-nav a.active { color: var(--color-teal); background: rgba(20,184,166,0.08); font-weight: 700; }
        .legal-content { padding: 32px; }
        @media (max-width: 720px) {
          .legal-layout { grid-template-columns: 1fr; }
          .legal-nav { position: static; flex-direction: row; flex-wrap: wrap; }
        }
      `}</style>
    </main>
  );
}

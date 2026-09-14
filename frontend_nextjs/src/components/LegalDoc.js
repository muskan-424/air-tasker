"use client";

export default function LegalDoc({ title, updated, children }) {
  return (
    <div className="legal-doc">
      <h1>{title}</h1>
      <p className="updated">Last updated: {updated}</p>
      {children}

      <style jsx>{`
        .legal-doc h1 { font-size: 1.6rem; font-weight: 800; margin-bottom: 4px; }
        .legal-doc .updated { color: var(--color-text-muted); font-size: 0.8rem; margin-bottom: 24px; }
        .legal-doc :global(h2) { font-size: 1.1rem; font-weight: 700; margin: 28px 0 10px; color: var(--color-teal); }
        .legal-doc :global(h2:first-of-type) { margin-top: 0; }
        .legal-doc :global(p) { color: var(--color-text-muted); line-height: 1.7; font-size: 0.92rem; margin: 0 0 12px; }
        .legal-doc :global(ul) { color: var(--color-text-muted); line-height: 1.7; font-size: 0.92rem; margin: 0 0 12px; padding-left: 22px; }
        .legal-doc :global(li) { margin-bottom: 6px; }
        .legal-doc :global(strong) { color: var(--color-text-main); }
        .legal-doc :global(a) { color: var(--color-teal); text-decoration: underline; }
      `}</style>
    </div>
  );
}

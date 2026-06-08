"use client";

import React, { useState } from "react";
import Link from "next/link";
import { CheckCircle2, FileText, Loader2, Rocket } from "lucide-react";
import { draftsAPI, tasksAPI } from "@/lib/api";

function defaultSchema(schema = {}) {
  return {
    category: schema.category || "General Service",
    title: schema.title || "",
    description: schema.description || "",
    location: schema.location || "",
    suggestedPriceRange: schema.suggestedPriceRange || { min: 600, max: 1200 },
  };
}

export default function TaskDraftReviewCard({ draftId, initialSchema, onPublished }) {
  const [schema, setSchema] = useState(() => defaultSchema(initialSchema));
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState(null);
  const [publishedTaskId, setPublishedTaskId] = useState(null);

  const updateField = (field, value) => {
    setSchema((prev) => ({ ...prev, [field]: value }));
  };

  const updatePrice = (key, value) => {
    setSchema((prev) => ({
      ...prev,
      suggestedPriceRange: {
        ...prev.suggestedPriceRange,
        [key]: Number(value) || 0,
      },
    }));
  };

  const handlePublish = async () => {
    if (!draftId || publishing) return;
    setPublishing(true);
    setError(null);
    try {
      await draftsAPI.update(draftId, schema);
      const task = await tasksAPI.publish(draftId);
      setPublishedTaskId(task.id);
      onPublished?.(task.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setPublishing(false);
    }
  };

  if (publishedTaskId) {
    return (
      <div className="draft-review-card published">
        <CheckCircle2 size={18} style={{ color: "var(--color-teal)" }} />
        <div>
          <strong>Task published</strong>
          <p>
            Live on the tasker feed.{" "}
            <Link href={`/tasks/${publishedTaskId}`}>View task</Link>
            {" · "}
            <Link href="/tasker">Browse feed</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="draft-review-card">
      <div className="draft-review-header">
        <FileText size={16} style={{ color: "var(--color-teal)" }} />
        <span>Review task draft</span>
        <code className="draft-id-chip">{draftId?.slice(0, 8)}…</code>
      </div>

      <div className="draft-review-grid">
        <label>
          Category
          <input value={schema.category} onChange={(e) => updateField("category", e.target.value)} />
        </label>
        <label>
          PIN / Location
          <input value={schema.location} onChange={(e) => updateField("location", e.target.value)} />
        </label>
        <label className="full-width">
          Title
          <input value={schema.title} onChange={(e) => updateField("title", e.target.value)} />
        </label>
        <label className="full-width">
          Description
          <textarea rows={3} value={schema.description} onChange={(e) => updateField("description", e.target.value)} />
        </label>
        <label>
          Min budget (₹)
          <input
            type="number"
            value={schema.suggestedPriceRange?.min ?? ""}
            onChange={(e) => updatePrice("min", e.target.value)}
          />
        </label>
        <label>
          Max budget (₹)
          <input
            type="number"
            value={schema.suggestedPriceRange?.max ?? ""}
            onChange={(e) => updatePrice("max", e.target.value)}
          />
        </label>
      </div>

      {error && <p className="draft-review-error">{error}</p>}

      <button type="button" className="btn-premium btn-teal draft-publish-btn" onClick={handlePublish} disabled={publishing}>
        {publishing ? <Loader2 size={16} className="spin-icon" /> : <Rocket size={16} />}
        {publishing ? "Publishing…" : "Publish to tasker feed"}
      </button>

      <style jsx>{`
        .draft-review-card {
          margin-top: 10px;
          padding: 14px;
          border-radius: 12px;
          border: 1px solid var(--border-teal);
          background: rgba(20, 184, 166, 0.04);
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .draft-review-card.published {
          flex-direction: row;
          align-items: flex-start;
          gap: 10px;
        }
        .draft-review-card.published p {
          margin: 4px 0 0;
          font-size: 0.85rem;
          color: var(--color-text-muted);
        }
        .draft-review-card.published a {
          color: var(--color-teal);
          text-decoration: underline;
        }
        .draft-review-header {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.85rem;
          font-weight: 700;
          color: var(--color-teal);
        }
        .draft-id-chip {
          margin-left: auto;
          font-size: 0.7rem;
          color: var(--color-text-muted);
        }
        .draft-review-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .draft-review-grid label {
          display: flex;
          flex-direction: column;
          gap: 4px;
          font-size: 0.72rem;
          font-weight: 600;
          text-transform: uppercase;
          color: var(--color-text-muted);
        }
        .draft-review-grid label.full-width {
          grid-column: 1 / -1;
        }
        .draft-review-grid input,
        .draft-review-grid textarea {
          background: rgba(7, 9, 19, 0.5);
          border: 1px solid var(--border-glow);
          border-radius: 8px;
          padding: 8px 10px;
          color: var(--color-text-main);
          font-family: inherit;
          font-size: 0.88rem;
        }
        .draft-review-error {
          color: #fca5a5;
          font-size: 0.82rem;
          margin: 0;
        }
        .draft-publish-btn {
          align-self: flex-start;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 0.85rem;
        }
        :global(.spin-icon) {
          animation: spin 1s linear infinite;
        }
        @media (max-width: 640px) {
          .draft-review-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}

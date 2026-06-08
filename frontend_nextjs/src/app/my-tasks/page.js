"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Briefcase, Loader2, MapPin, RefreshCw } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { tasksAPI } from "@/lib/api";

const STATUS_COLORS = {
  PUBLISHED: "#14b8a6",
  ACCEPTED: "#f59e0b",
  IN_PROGRESS: "#38bdf8",
  COMPLETED: "#10b981",
  CANCELLED: "#f87171",
};

export default function MyTasksPage() {
  const { isLoggedIn, user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadTasks = useCallback(async () => {
    if (!isLoggedIn) return;
    setLoading(true);
    setError(null);
    try {
      const data = await tasksAPI.mine(30);
      setTasks(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card page-card">
          <p>Please <Link href="/login">sign in</Link> to view your tasks.</p>
        </div>
      </main>
    );
  }

  const isTasker = user?.role === "TASKER";
  const title = isTasker ? "My Accepted Jobs" : "My Posted Tasks";

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          <p>
            {isTasker
              ? "Tasks you have accepted and are working on."
              : "Tasks you created and published on VayuTask AI."}
          </p>
        </div>
        <button type="button" className="btn-premium btn-teal" onClick={loadTasks} disabled={loading}>
          <RefreshCw size={16} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
          Refresh
        </button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">
          <Loader2 size={24} className="spin-icon" />
          Loading tasks...
        </div>
      ) : tasks.length === 0 ? (
        <div className="glass-card empty-state">
          <Briefcase size={28} />
          <p>No tasks yet.</p>
          <Link href={isTasker ? "/tasker" : "/poster"} className="btn-premium btn-saffron">
            {isTasker ? "Browse Task Radar" : "Create a Task"}
          </Link>
        </div>
      ) : (
        <div className="task-grid">
          {tasks.map((task) => {
            const schema = task.task_schema || {};
            const statusColor = STATUS_COLORS[task.status] || "#94a3b8";
            return (
              <Link key={task.id} href={`/tasks/${task.id}`} className="glass-card task-card">
                <div className="task-card-top">
                  <span className="cat-chip">{task.category || "General"}</span>
                  <span className="status-chip" style={{ color: statusColor, borderColor: `${statusColor}55` }}>
                    {task.status}
                  </span>
                </div>
                <h3>{schema.title || task.subcategory || "Untitled task"}</h3>
                <p className="task-desc">{schema.description || "No description provided."}</p>
                <div className="task-meta">
                  <MapPin size={14} />
                  {schema.location || schema.location_pin || "India"}
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <style jsx>{`
        .page-shell { max-width: 1100px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 24px; }
        .page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
        .page-header h1 { font-size: 2rem; font-weight: 800; }
        .page-header p { color: var(--color-text-muted); margin-top: 6px; max-width: 520px; }
        .error-banner { padding: 12px 16px; border-radius: 10px; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5; }
        .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 48px 24px; text-align: center; color: var(--color-text-muted); }
        .task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
        .task-card { padding: 20px; text-decoration: none; color: inherit; display: flex; flex-direction: column; gap: 10px; }
        .task-card-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
        .cat-chip { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: var(--color-teal); }
        .status-chip { font-size: 0.68rem; font-weight: 700; padding: 3px 8px; border-radius: 999px; border: 1px solid; }
        .task-card h3 { font-size: 1.05rem; font-weight: 700; }
        .task-desc { font-size: 0.85rem; color: var(--color-text-muted); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .task-meta { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: var(--color-text-muted); }
        :global(.spin-icon) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

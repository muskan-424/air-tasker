"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { RefreshCw, CheckCircle2, Scan, Layers, Timer, MapPin, AlertTriangle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { tasksAPI } from "@/lib/api";

const CATEGORY_COLORS = {
  Electrical: { ring: "#f59e0b", glow: "rgba(245,158,11,0.15)" },
  Plumbing: { ring: "#06b6d4", glow: "rgba(6,182,212,0.15)" },
  Cleaning: { ring: "#a78bfa", glow: "rgba(167,139,250,0.15)" },
  Gardening: { ring: "#34d399", glow: "rgba(52,211,153,0.15)" },
  Painting: { ring: "#f87171", glow: "rgba(248,113,113,0.15)" },
  General: { ring: "#14b8a6", glow: "rgba(20,184,166,0.15)" },
};

function getColor(category) {
  const key = Object.keys(CATEGORY_COLORS).find((k) =>
    (category || "").toLowerCase().includes(k.toLowerCase())
  );
  return CATEGORY_COLORS[key || "General"];
}

export default function TaskerRadar() {
  const { isLoggedIn } = useAuth();
  const canvasRef = useRef(null);
  const animFrameRef = useRef(null);
  const angleRef = useRef(0);

  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [acceptedIds, setAcceptedIds] = useState(new Set());
  const [acceptingId, setAcceptingId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [filterCategory, setFilterCategory] = useState("");
  const [pinInput, setPinInput] = useState("");
  const [pinSuccess, setPinSuccess] = useState(false);

  // ── Fetch tasks from backend ──────────────────────────────────────────────
  const fetchTasks = useCallback(async () => {
    if (!isLoggedIn) return;
    setLoading(true);
    setApiError(null);
    try {
      const data = await tasksAPI.feed(filterCategory || null, 20);
      setTasks(data);
    } catch (err) {
      setApiError(err.message);
      // Show mock data so UI is still useful when backend is down
      setTasks([
        { id: "demo-1", category: "Electrical", subcategory: "AC Repair", task_schema: { title: "AC Leak Fix", location: "110001", estimated_duration_minutes: 90, suggested_price_range: { min: 800, max: 1200 } }, status: "published" },
        { id: "demo-2", category: "Plumbing", subcategory: "Pipe Fix", task_schema: { title: "Burst Pipe Repair", location: "400001", estimated_duration_minutes: 60, suggested_price_range: { min: 500, max: 900 } }, status: "published" },
        { id: "demo-3", category: "Cleaning", subcategory: "Deep Clean", task_schema: { title: "3BHK Deep Clean", location: "560001", estimated_duration_minutes: 240, suggested_price_range: { min: 1500, max: 2500 } }, status: "published" },
      ]);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn, filterCategory]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  // ── Accept task: POST /api/tasks/{task_id}/accept ─────────────────────────
  const handleAccept = async (taskId, e) => {
    e.stopPropagation();
    if (!isLoggedIn) { window.location.href = "/login"; return; }
    setAcceptingId(taskId);
    try {
      await tasksAPI.accept(taskId);
      setAcceptedIds((prev) => new Set([...prev, taskId]));
      alert(`✅ Task accepted! You can now proceed to the payment & verification flow.\n\nTask ID: ${taskId}`);
      window.location.href = `/payments?task_id=${taskId}`;
    } catch (err) {
      alert(`Accept failed: ${err.message}`);
    } finally {
      setAcceptingId(null);
    }
  };

  // ── Radar canvas animation ────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const R = cx - 10;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      // Grid rings
      [0.25, 0.5, 0.75, 1].forEach((r) => {
        ctx.beginPath();
        ctx.arc(cx, cy, R * r, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(20,184,166,0.15)";
        ctx.lineWidth = 1;
        ctx.stroke();
      });
      // Cross hairs
      ctx.strokeStyle = "rgba(20,184,166,0.1)";
      ctx.beginPath(); ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy); ctx.stroke();

      // Sweep gradient
      const sweep = ctx.createConicalGradient ? null : null;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angleRef.current);
      const grad = ctx.createLinearGradient(0, 0, R, 0);
      grad.addColorStop(0, "rgba(20,184,166,0.5)");
      grad.addColorStop(1, "rgba(20,184,166,0)");
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, R, -0.3, 0.3);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.restore();

      // Task dots
      tasks.slice(0, 12).forEach((task, i) => {
        const angle = (i / Math.max(tasks.length, 1)) * Math.PI * 2;
        const dist = 0.3 + (i % 3) * 0.22;
        const x = cx + R * dist * Math.cos(angle);
        const y = cy + R * dist * Math.sin(angle);
        const color = getColor(task.category).ring;
        const isAcc = acceptedIds.has(task.id);
        ctx.beginPath();
        ctx.arc(x, y, isAcc ? 8 : 5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        if (isAcc) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      });

      angleRef.current += 0.02;
      animFrameRef.current = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [tasks, acceptedIds]);

  // ── PIN unlock simulation ─────────────────────────────────────────────────
  const handlePinSubmit = (e) => {
    e.preventDefault();
    if (pinInput.trim().length >= 4) {
      setPinSuccess(true);
      setTimeout(() => setPinSuccess(false), 3000);
    }
  };

  return (
    <div className="radar-wrapper">
      <div className="radar-header-box">
        <h2 className="title-gradient-saffron">Tasker Radar Feed</h2>
        <p>Live tasks from the FastAPI backend. Accept and trace to the payment escrow flow.</p>
      </div>

      {!isLoggedIn && (
        <div className="auth-warning">
          <AlertTriangle className="warn-icon" /> <span>You must <a href="/login">sign in</a> as a Tasker to accept tasks.</span>
        </div>
      )}

      {apiError && (
        <div className="api-error-bar">
          ⚠ Backend note: {apiError} — showing demo tasks.
        </div>
      )}

      <div className="radar-grid">
        {/* Left: Radar Canvas */}
        <div className="glass-card radar-canvas-card">
          <div className="canvas-header">
            <Scan style={{ width: 18, height: 18, color: "var(--color-teal)" }} />
            <span>Live Radar — {tasks.length} tasks</span>
            <button onClick={fetchTasks} disabled={loading} className="refresh-btn" title="Refresh">
              <RefreshCw style={{ width: 14, height: 14, animation: loading ? "spin 1s linear infinite" : "none" }} />
            </button>
          </div>
          <div className="canvas-wrapper">
            <canvas ref={canvasRef} width="280" height="280" className="radar-canvas"></canvas>
          </div>

          {/* Filter */}
          <div className="filter-row">
            <label className="filter-label">Filter by Category:</label>
            <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} className="category-select">
              <option value="">All Categories</option>
              {Object.keys(CATEGORY_COLORS).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* PIN for real-world scenario */}
          <form onSubmit={handlePinSubmit} className="pin-form">
            <input
              type="text"
              placeholder="Enter location PIN code..."
              value={pinInput}
              onChange={(e) => setPinInput(e.target.value.replace(/\D/, "").slice(0, 6))}
              className="pin-input"
              maxLength={6}
            />
            <button type="submit" className="btn-premium btn-teal pin-btn">
              {pinSuccess ? "✓ Matched" : "Scan Area"}
            </button>
          </form>
        </div>

        {/* Right: Task Cards */}
        <div className="task-list-col">
          {loading && (
            <div className="loading-msg">
              <RefreshCw style={{ animation: "spin 1s linear infinite" }} /> Fetching tasks from backend...
            </div>
          )}
          {!loading && tasks.length === 0 && (
            <div className="empty-msg">No tasks found. <a href="/poster" style={{ color: "var(--color-teal)" }}>Post one!</a></div>
          )}
          {tasks.map((task) => {
            const schema = task.task_schema || {};
            const priceRange = schema.suggested_price_range || schema.suggestedPriceRange || {};
            const color = getColor(task.category);
            const isAcc = acceptedIds.has(task.id);
            const isAccepting = acceptingId === task.id;
            return (
              <div
                key={task.id}
                className={`task-card glass-card ${isAcc ? "task-accepted" : ""}`}
                style={{ "--ring-color": color.ring, "--glow-color": color.glow }}
                onClick={() => setSelected(selected?.id === task.id ? null : task)}
              >
                <div className="task-card-header">
                  <div className="task-cat-badge" style={{ color: color.ring, borderColor: color.ring }}>
                    {task.category || "General"}
                  </div>
                  <div className="task-status-pill">
                    {isAcc ? (
                      <><CheckCircle2 style={{ width: 12, height: 12, color: "#10b981" }} /> Accepted</>
                    ) : (
                      <><div className="pulse-marker-teal" style={{ width: 8, height: 8, borderRadius: "50%" }}></div> Available</>
                    )}
                  </div>
                </div>

                <h4 className="task-title">{schema.title || task.subcategory || "Task"}</h4>

                <div className="task-meta">
                  <span><MapPin style={{ width: 12, height: 12 }} /> {schema.location || task.task_schema?.location || "India"}</span>
                  <span><Timer style={{ width: 12, height: 12 }} /> {schema.estimated_duration_minutes || 60} min</span>
                  {priceRange.min && (
                    <span><Layers style={{ width: 12, height: 12 }} /> ₹{priceRange.min}–₹{priceRange.max}</span>
                  )}
                </div>

                {selected?.id === task.id && (
                  <div className="task-detail-expanded">
                    <p className="task-desc">{schema.description || "Task description from backend."}</p>
                    {schema.completion_criteria && (
                      <p><b>Completion:</b> {schema.completion_criteria}</p>
                    )}
                    <p className="task-id-label">ID: <code>{task.id}</code></p>
                  </div>
                )}

                {!isAcc && (
                  <div className="task-card-actions">
                    <div className="checklist-items">
                      <label className="check-item"><input type="checkbox" defaultChecked /> I have the required tools</label>
                      <label className="check-item"><input type="checkbox" defaultChecked /> I can meet the location</label>
                    </div>
                    <button
                      onClick={(e) => handleAccept(task.id, e)}
                      disabled={isAccepting}
                      className="btn-premium btn-saffron accept-btn"
                    >
                      {isAccepting ? "Accepting..." : "Accept & Proceed →"}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .radar-wrapper { display: flex; flex-direction: column; gap: 40px; }
        .radar-header-box { text-align: center; }
        .title-gradient-saffron { font-size: 2.2rem; font-weight: 800; background: linear-gradient(135deg, var(--color-saffron) 0%, #d97706 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .auth-warning { display: flex; align-items: center; gap: 8px; justify-content: center; background: rgba(245,158,11,0.07); border: 1px solid rgba(245,158,11,0.2); border-radius: 10px; padding: 12px 20px; color: var(--color-saffron); font-size: 0.85rem; font-weight: 600; }
        .warn-icon { width: 16px; height: 16px; }
        .auth-warning a { color: var(--color-teal); text-decoration: underline; }
        .api-error-bar { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 0.85rem; }
        .radar-grid { display: grid; grid-template-columns: 340px 1fr; gap: 30px; align-items: start; }
        .radar-canvas-card { padding: 24px; display: flex; flex-direction: column; gap: 18px; }
        .canvas-header { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 600; color: var(--color-text-muted); }
        .refresh-btn { margin-left: auto; width: 28px; height: 28px; border-radius: 6px; background: rgba(20,184,166,0.1); border: 1px solid var(--border-teal); color: var(--color-teal); display: flex; align-items: center; justify-content: center; cursor: pointer; }
        .canvas-wrapper { display: flex; justify-content: center; }
        .radar-canvas { border-radius: 50%; background: radial-gradient(circle, rgba(7,9,19,0.95) 0%, rgba(7,9,19,0.8) 100%); }
        .filter-row { display: flex; flex-direction: column; gap: 6px; }
        .filter-label { font-size: 0.75rem; font-weight: 700; color: var(--color-text-muted); text-transform: uppercase; }
        .category-select { background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px; padding: 8px 12px; color: var(--color-text-main); font-family: inherit; font-size: 0.9rem; outline: none; width: 100%; cursor: pointer; }
        .pin-form { display: flex; gap: 8px; }
        .pin-input { flex: 1; background: rgba(7,9,19,0.6); border: 1px solid var(--border-glow); border-radius: 8px; padding: 10px 12px; color: var(--color-text-main); font-family: monospace; font-size: 1rem; letter-spacing: 0.1em; outline: none; text-align: center; }
        .pin-btn { padding: 10px 16px; }
        .task-list-col { display: flex; flex-direction: column; gap: 16px; }
        .loading-msg, .empty-msg { display: flex; align-items: center; gap: 10px; color: var(--color-text-muted); font-size: 0.9rem; padding: 24px; justify-content: center; }
        .task-card { padding: 22px; cursor: pointer; border: 1px solid var(--border-glow); transition: all 0.3s ease; display: flex; flex-direction: column; gap: 14px; }
        .task-card:hover { border-color: var(--ring-color); box-shadow: 0 0 20px var(--glow-color); }
        .task-accepted { border-color: #10b981 !important; background: rgba(16,185,129,0.03) !important; }
        .task-card-header { display: flex; justify-content: space-between; align-items: center; }
        .task-cat-badge { font-size: 0.7rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; border: 1px solid; text-transform: uppercase; background: rgba(255,255,255,0.03); }
        .task-status-pill { display: flex; align-items: center; gap: 5px; font-size: 0.72rem; font-weight: 600; color: var(--color-text-muted); }
        .task-title { font-size: 1.05rem; font-weight: 700; }
        .task-meta { display: flex; gap: 14px; flex-wrap: wrap; }
        .task-meta span { display: flex; align-items: center; gap: 5px; font-size: 0.78rem; color: var(--color-text-muted); }
        .task-detail-expanded { padding-top: 12px; border-top: 1px solid var(--border-glow); display: flex; flex-direction: column; gap: 8px; }
        .task-desc { font-size: 0.85rem; color: var(--color-text-muted); line-height: 1.5; }
        .task-id-label { font-size: 0.75rem; color: var(--color-text-muted); } .task-id-label code { color: var(--color-teal); }
        .task-card-actions { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; padding-top: 8px; border-top: 1px solid var(--border-glow); }
        .checklist-items { display: flex; flex-direction: column; gap: 6px; }
        .check-item { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: var(--color-text-muted); cursor: pointer; }
        .check-item input { accent-color: var(--color-teal); }
        .accept-btn { margin-left: auto; }
        @media (max-width: 900px) { .radar-grid { grid-template-columns: 1fr; } }
      ` }} />
    </div>
  );
}

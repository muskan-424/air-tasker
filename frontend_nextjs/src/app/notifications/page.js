"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, CheckCheck, Loader, Settings, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { notificationsAPI } from "@/lib/api";
import {
  CATEGORY_COLORS,
  filterNotifications,
  formatNotificationTime,
  getNotificationAction,
  normalizeNotification,
} from "@/lib/notifications";

const TABS = ["all", "unread", "task", "escrow", "system"];

export default function NotificationsPage() {
  const { isLoggedIn, token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [tab, setTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [prefs, setPrefs] = useState(null);
  const [prefsOpen, setPrefsOpen] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [markingId, setMarkingId] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);

  const loadNotifications = useCallback(async () => {
    if (!isLoggedIn) return;
    setLoading(true);
    try {
      const data = await notificationsAPI.list(50);
      setNotifications((data || []).map(normalizeNotification).filter(Boolean));
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [isLoggedIn]);

  const loadPrefs = useCallback(async () => {
    if (!isLoggedIn) return;
    try {
      const data = await notificationsAPI.getPreferences();
      setPrefs(data);
    } catch {
      setPrefs(null);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    loadNotifications();
    loadPrefs();
  }, [loadNotifications, loadPrefs]);

  useEffect(() => {
    if (!isLoggedIn || !token) return;

    const connect = () => {
      const ws = new WebSocket(notificationsAPI.buildWsUrl(token));
      wsRef.current = ws;

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        if (wsRef.current === ws) setTimeout(connect, 4000);
      };

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          const item = normalizeNotification(msg);
          if (item?.id) {
            setNotifications((prev) => {
              if (prev.some((n) => n.id === item.id)) return prev;
              return [item, ...prev].slice(0, 100);
            });
          }
        } catch { /* ignore */ }
      };

      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 25000);

      return () => {
        clearInterval(ping);
        ws.close(1000);
      };
    };

    const cleanup = connect();
    return () => {
      cleanup?.();
      wsRef.current?.close(1000);
    };
  }, [isLoggedIn, token]);

  const unreadCount = notifications.filter((n) => !n.read_at).length;
  const visible = filterNotifications(notifications, tab);

  const markRead = async (id) => {
    setMarkingId(id);
    try {
      await notificationsAPI.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
    } catch { /* silent */ }
    setMarkingId(null);
  };

  const markAllRead = async () => {
    const unread = notifications.filter((n) => !n.read_at);
    await Promise.all(unread.map((n) => notificationsAPI.markRead(n.id).catch(() => {})));
    setNotifications((prev) =>
      prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
    );
  };

  const togglePref = async (key) => {
    if (!prefs) return;
    setSavingPrefs(true);
    const next = { ...prefs, [key]: !prefs[key] };
    setPrefs(next);
    try {
      const saved = await notificationsAPI.updatePreferences({ [key]: next[key] });
      setPrefs(saved);
    } catch {
      setPrefs(prefs);
    } finally {
      setSavingPrefs(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <main className="page-shell">
        <div className="glass-card page-card">
          <p>Please <Link href="/login">sign in</Link> to view notifications.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <h1><Bell size={28} /> Notifications</h1>
          <p>In-app alerts for tasks, escrow, and disputes. {wsConnected ? "Live updates on." : "Connecting…"}</p>
        </div>
        <div className="header-actions">
          {unreadCount > 0 && (
            <button type="button" className="btn-premium btn-outline" onClick={markAllRead}>
              <CheckCheck size={16} /> Mark all read
            </button>
          )}
          <button type="button" className="btn-premium btn-teal" onClick={() => setPrefsOpen((o) => !o)}>
            <Settings size={16} /> Preferences
          </button>
        </div>
      </header>

      {prefsOpen && prefs && (
        <div className="glass-card prefs-card">
          <h3>Notification preferences</h3>
          <div className="prefs-grid">
            {[
              ["in_app_enabled", "In-app notifications"],
              ["email_enabled", "Email notifications (master)"],
              ["email_task", "Email: task updates"],
              ["email_escrow", "Email: escrow events"],
              ["email_dispute", "Email: disputes"],
            ].map(([key, label]) => (
              <label key={key} className="pref-row">
                <input
                  type="checkbox"
                  checked={!!prefs[key]}
                  disabled={savingPrefs}
                  onChange={() => togglePref(key)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            className={`tab-btn ${tab === t ? "tab-active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
            {t === "unread" && unreadCount > 0 && <span className="tab-badge">{unreadCount}</span>}
          </button>
        ))}
      </div>

      <div className="glass-card list-card">
        {loading ? (
          <div className="empty"><Loader className="spin" size={24} /> Loading…</div>
        ) : visible.length === 0 ? (
          <div className="empty">
            <Zap size={28} style={{ opacity: 0.35 }} />
            <p>No notifications in this view.</p>
            <span className="hint">Accept a task or start escrow to generate alerts.</span>
          </div>
        ) : (
          visible.map((n) => {
            const cat = (n.category || "SYSTEM").toUpperCase();
            const style = CATEGORY_COLORS[cat] || CATEGORY_COLORS.SYSTEM;
            const isUnread = !n.read_at;
            const cta = getNotificationAction(n);
            return (
              <article
                key={n.id}
                className={`notif-row ${isUnread ? "unread" : ""}`}
                onClick={() => isUnread && markRead(n.id)}
              >
                <span className="dot" style={{ background: style.color }} />
                <div className="body">
                  <div className="row-top">
                    <span className="chip" style={{ color: style.color, background: style.bg }}>{cat}</span>
                    <time>{formatNotificationTime(n.created_at)}</time>
                  </div>
                  <h4>{n.title}</h4>
                  <p>{n.body}</p>
                  {cta && (
                    <Link href={cta.href} className="cta" onClick={(e) => e.stopPropagation()}>
                      {cta.label} →
                    </Link>
                  )}
                </div>
                {isUnread && (
                  <button
                    type="button"
                    className="read-btn"
                    disabled={markingId === n.id}
                    onClick={(e) => { e.stopPropagation(); markRead(n.id); }}
                    title="Mark read"
                  >
                    <CheckCheck size={14} />
                  </button>
                )}
              </article>
            );
          })
        )}
      </div>

      <style jsx>{`
        .page-shell { max-width: 760px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
        .page-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 16px; }
        h1 { display: flex; align-items: center; gap: 10px; font-size: 1.8rem; font-weight: 800; }
        .page-header p { color: var(--color-text-muted); font-size: 0.9rem; margin-top: 6px; }
        .header-actions { display: flex; flex-wrap: wrap; gap: 10px; }
        .prefs-card { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
        .prefs-card h3 { font-size: 1rem; font-weight: 700; }
        .prefs-grid { display: flex; flex-direction: column; gap: 10px; }
        .pref-row { display: flex; align-items: center; gap: 10px; font-size: 0.88rem; color: var(--color-text-muted); cursor: pointer; }
        .tabs { display: flex; flex-wrap: wrap; gap: 8px; }
        .tab-btn {
          padding: 6px 14px; border-radius: 999px; border: 1px solid var(--border-glow);
          background: transparent; color: var(--color-text-muted); font-size: 0.78rem;
          font-weight: 700; text-transform: capitalize; cursor: pointer; font-family: inherit;
          display: inline-flex; align-items: center; gap: 6px;
        }
        .tab-active { color: var(--color-teal); border-color: var(--border-teal); background: rgba(20,184,166,0.08); }
        .tab-badge { background: #ef4444; color: white; font-size: 0.62rem; padding: 1px 6px; border-radius: 8px; }
        .list-card { padding: 0; overflow: hidden; }
        .notif-row {
          display: flex; gap: 12px; padding: 16px 18px; border-bottom: 1px solid var(--border-glow);
          cursor: pointer; transition: background 0.15s;
        }
        .notif-row:last-child { border-bottom: none; }
        .notif-row:hover { background: rgba(255,255,255,0.02); }
        .notif-row.unread { background: rgba(20,184,166,0.03); }
        .dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
        .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
        .row-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .chip { font-size: 0.62rem; font-weight: 700; padding: 2px 8px; border-radius: 8px; text-transform: uppercase; }
        time { font-size: 0.72rem; color: var(--color-text-muted); }
        h4 { font-size: 0.9rem; font-weight: 700; }
        p { font-size: 0.82rem; color: var(--color-text-muted); line-height: 1.45; }
        .cta { font-size: 0.75rem; font-weight: 700; color: var(--color-teal); text-decoration: none; margin-top: 4px; }
        .read-btn {
          width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--border-teal);
          background: rgba(20,184,166,0.08); color: var(--color-teal); cursor: pointer;
          display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        .empty { padding: 48px 24px; display: flex; flex-direction: column; align-items: center; gap: 10px; color: var(--color-text-muted); text-align: center; }
        .hint { font-size: 0.78rem; opacity: 0.8; }
        :global(.spin) { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}

"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useBeta, isNavEnabled } from "@/context/BetaContext";
import { healthAPI, notificationsAPI, tasksAPI } from "@/lib/api";
import {
  CATEGORY_COLORS,
  filterNotifications,
  getNotificationAction,
  normalizeNotification,
} from "@/lib/notifications";
import {
  LogOut, Bell, CheckCheck, Zap, MessageSquare,
  ShieldCheck, CreditCard, Radio, PenLine, Menu, X,
  Search, ChevronDown, Sparkles, User, Settings,
  Keyboard, CornerDownLeft, Activity, Info, LayoutDashboard
} from "lucide-react";

const NAV_LINKS = [
  { href: "/poster",   label: "Poster Sandbox", icon: PenLine },
  { href: "/tasker",   label: "Tasker Radar",   icon: Radio },
  { href: "/my-tasks", label: "My Tasks",       icon: LayoutDashboard },
  { href: "/profile",  label: "Profile",        icon: User },
  { href: "/kyc",      label: "KYC & Payout",   icon: ShieldCheck },
  { href: "/chat",     label: "AI Chat",         icon: MessageSquare },
  { href: "/notifications", label: "Alerts",     icon: Bell },
  { href: "/verify",   label: "Vision Proof",    icon: ShieldCheck },
  { href: "/payments", label: "Payments",        icon: CreditCard },
  { href: "/feedback", label: "Feedback",        icon: MessageSquare },
];

export default function NavBar() {
  const { user, token, isLoggedIn, logout } = useAuth();
  const { config: betaConfig } = useBeta();
  const pathname = usePathname();
  const navLinks = NAV_LINKS.filter((link) => isNavEnabled(link.href, betaConfig.feature_flags));

  // ── Basic State ───────────────────────────────────────────────────────────
  const [apiOnline, setApiOnline]           = useState(null);
  const [notifications, setNotifications]   = useState([]);
  const [unreadCount, setUnreadCount]       = useState(0);
  const [notifOpen, setNotifOpen]           = useState(false);
  const [mobileOpen, setMobileOpen]         = useState(false);
  const [markingId, setMarkingId]           = useState(null);

  // ── Advanced UX States ─────────────────────────────────────────────────────
  const [scrolled, setScrolled]             = useState(false);
  const [shouldShake, setShouldShake]       = useState(false);
  const [userMenuOpen, setUserMenuOpen]     = useState(false);
  const [paletteOpen, setPaletteOpen]       = useState(false);
  const [searchQuery, setSearchQuery]       = useState("");
  const [selectedIdx, setSelectedIdx]       = useState(0);
  
  // Advanced Features State
  const [hoveredRect, setHoveredRect]       = useState(null);
  const [apiLatency, setApiLatency]         = useState(null);
  const [notifTab, setNotifTab]             = useState("all"); // all, unread, system, escrow
  const [userStatus, setUserStatus]         = useState("online"); // online, busy, away
  const [tasksFeed, setTasksFeed]           = useState([]); // Dynamic palette tasks query

  const notifRef      = useRef(null);
  const userMenuRef   = useRef(null);
  const paletteRef    = useRef(null);
  const wsRef         = useRef(null);
  const navLinksRef   = useRef(null);

  // ── Magnetic Link Highlight Calculation ──────────────────────────────────
  const handleLinkMouseEnter = (e) => {
    const link = e.currentTarget;
    const parent = navLinksRef.current;
    if (link && parent) {
      const linkRect = link.getBoundingClientRect();
      const parentRect = parent.getBoundingClientRect();
      setHoveredRect({
        left: linkRect.left - parentRect.left,
        width: linkRect.width,
        height: linkRect.height,
        opacity: 1
      });
    }
  };

  const handleLinkMouseLeave = () => {
    setHoveredRect((prev) => prev ? { ...prev, opacity: 0 } : null);
  };

  // ── Scroll aware shrink ────────────────────────────────────────────────────
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // ── Keyboard Cmd+K / Escape Listener ───────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
      if (e.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // ── API Health Polling with Latency Metric ─────────────────────────────────
  useEffect(() => {
    const check = async () => {
      const start = performance.now();
      try {
        await healthAPI.check();
        const duration = Math.round(performance.now() - start);
        setApiLatency(duration);
        setApiOnline(true);
      } catch {
        setApiOnline(false);
        setApiLatency(null);
      }
    };
    check();
    const id = setInterval(check, 15000);
    return () => clearInterval(id);
  }, []);

  // ── Fetch notifications ────────────────────────────────────────────────────
  const fetchNotifications = useCallback(async () => {
    if (!isLoggedIn) return;
    try {
      const data = await notificationsAPI.list(20);
      const normalized = (data || []).map(normalizeNotification).filter(Boolean);
      setNotifications(normalized);
      setUnreadCount(normalized.filter((n) => !n.read_at).length);
    } catch { /* silent — backend may be offline */ }
  }, [isLoggedIn]);

  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  // ── WebSocket listener with bell shake micro-interaction ───────────────────
  useEffect(() => {
    if (!isLoggedIn || !token) return;

    const connect = () => {
      const url = notificationsAPI.buildWsUrl(token);
      const ws  = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          const item = normalizeNotification(msg);
          if (item?.id) {
            setNotifications((prev) => {
              if (prev.some((n) => n.id === item.id)) return prev;
              return [item, ...prev].slice(0, 30);
            });
            setUnreadCount((c) => c + 1);
            setShouldShake(true);
            setTimeout(() => setShouldShake(false), 800);
          }
        } catch {}
      };

      ws.onclose = (e) => {
        if (e.code !== 1000 && e.code !== 1008) setTimeout(connect, 4000);
      };

      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 25000);

      ws.onerror = () => clearInterval(ping);
      return () => { clearInterval(ping); ws.close(1000); };
    };

    const cleanup = connect();
    return () => { cleanup?.(); wsRef.current?.close(1000); };
  }, [isLoggedIn, token]);

  // ── Fetch tasks feed on command palette activation ─────────────────────────
  useEffect(() => {
    if (paletteOpen) {
      tasksAPI.feed().then((data) => setTasksFeed(data || [])).catch(() => {});
    }
  }, [paletteOpen]);

  // ── Mark single notification as read ──────────────────────────────────────
  const markRead = async (id) => {
    setMarkingId(id);
    try {
      await notificationsAPI.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => n.id === id ? { ...n, read_at: new Date().toISOString() } : n)
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {}
    setMarkingId(null);
  };

  // ── Mark all read ─────────────────────────────────────────────────────────
  const markAllRead = async () => {
    const unread = notifications.filter((n) => !n.read_at);
    await Promise.all(unread.map((n) => notificationsAPI.markRead(n.id).catch(() => {})));
    setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() })));
    setUnreadCount(0);
  };

  // ── Click outside to close dropdowns ──────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false);
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) setUserMenuOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ── Close mobile menu on route change ─────────────────────────────────────
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // ── Autofocus command palette input ───────────────────────────────────────
  useEffect(() => {
    if (paletteOpen) {
      setTimeout(() => {
        const input = document.getElementById("vt-palette-input");
        if (input) input.focus();
      }, 50);
      setSelectedIdx(0);
    }
  }, [paletteOpen]);

  // ── Command Palette combined navigation & live queries ────────────────────
  const paletteActions = [
    { title: "Poster Sandbox", subtitle: "Draft, translate, and post gigs", href: "/poster", icon: PenLine, category: "Navigation" },
    { title: "Tasker Radar Feed", subtitle: "Browse live local jobs and accept work", href: "/tasker", icon: Radio, category: "Navigation" },
    { title: "AI Translation Chat", subtitle: "Real-time communication with translation", href: "/chat", icon: MessageSquare, category: "Navigation" },
    { title: "Vision Proof Verification", subtitle: "Validate completed works using AI analysis", href: "/verify", icon: ShieldCheck, category: "Navigation" },
    { title: "Escrow & Ledger Payments", subtitle: "Secure transactions and payment logs", href: "/payments", icon: CreditCard, category: "Navigation" },
    { title: "Post a New Task Draft", subtitle: "Fast track to create a gig listing", href: "/poster", icon: Sparkles, category: "Quick Actions" },
    { title: "Notification Center", subtitle: "Full inbox, filters, and preferences", href: "/notifications", icon: Bell, category: "Navigation" },
    { title: "Open Notifications Feed", subtitle: "Toggle bell dropdown in navbar", action: "open_notifications", icon: Bell, category: "Quick Actions" },
    { title: "System Connection Check", subtitle: "Inspect FastAPI backend API status", action: "check_health", icon: Activity, category: "System" },
    { title: "Sign Out Session", subtitle: "Clear credentials and log out", action: "logout", icon: LogOut, category: "Account", authRequired: true }
  ];

  const filteredActions = paletteActions.filter(item => {
    if (item.authRequired && !isLoggedIn) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.subtitle.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    );
  });

  const filteredTasks = searchQuery
    ? tasksFeed.filter(task =>
        task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.description.toLowerCase().includes(searchQuery.toLowerCase())
      ).slice(0, 5)
    : tasksFeed.slice(0, 3);

  // Combine static and query matches for integrated keyboard scrolling
  const combinedPaletteItems = [
    ...filteredActions,
    ...filteredTasks.map(task => ({
      title: task.title,
      subtitle: `Radar Task • ₹${task.budget?.toLocaleString() || "0"} • Category: ${task.category || "General"}`,
      href: `/payments?task_id=${task.id}`,
      icon: Radio,
      category: "Tasks on Radar"
    }))
  ];

  const handlePaletteAction = (item) => {
    setPaletteOpen(false);
    setSearchQuery("");
    if (item.href) {
      window.location.href = item.href;
    } else if (item.action === "open_notifications") {
      setNotifOpen(true);
      fetchNotifications();
    } else if (item.action === "check_health") {
      alert(`VayuTask Engine Latency: ${apiLatency ? `${apiLatency}ms (FastAPI Connected)` : "Offline"}`);
    } else if (item.action === "logout") {
      logout();
    }
  };

  const handlePaletteKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((prev) => (prev + 1) % Math.max(1, combinedPaletteItems.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((prev) => (prev - 1 + combinedPaletteItems.length) % Math.max(1, combinedPaletteItems.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (combinedPaletteItems[selectedIdx]) {
        handlePaletteAction(combinedPaletteItems[selectedIdx]);
      }
    }
  };

  // ── Notification Tab Filtering & CTA Links ───────────────────────────────
  const filteredNotifs = filterNotifications(notifications, notifTab);

  const getActionCTA = getNotificationAction;

  const statusColor = apiOnline === null ? "#94a3b8" : apiOnline ? "#10b981" : "#ef4444";
  const statusLabel = apiOnline === null ? "Checking..." : apiOnline ? `Online • ${apiLatency || 0}ms` : "Offline";

  return (
    <>
      {/* ── Top Premium Pulse Energy Accent Line ──────────────────────────────── */}
      <div className="vt-top-accent" />

      <header className={`vt-nav ${scrolled ? "vt-nav-scrolled" : ""}`}>
        <div className="vt-nav-inner">

          {/* ── Logo ──────────────────────────────────────────────────────── */}
          <a href="/" className="vt-logo">
            <span className="vt-logo-dot"></span>
            VayuTask <span className="vt-logo-badge">AI</span>
          </a>

          {/* ── Command Search Button Trigger ─────────────────────────────── */}
          <button className="vt-search-trigger" onClick={() => setPaletteOpen(true)} title="Search tools & actions (Ctrl+K)">
            <Search className="vt-search-icon" />
            <span className="vt-search-placeholder">Search workspace...</span>
            <span className="vt-search-kbd">
              <Keyboard style={{ width: 11, height: 11 }} />
              <span>K</span>
            </span>
          </button>

          {/* ── Magnetic Nav Links ────────────────────────────────────────── */}
          <nav className="vt-links" ref={navLinksRef} onMouseLeave={handleLinkMouseLeave}>
            
            {/* Sliding Highlight Pill */}
            <div
              className="vt-link-highlight"
              style={{
                transform: hoveredRect ? `translateX(${hoveredRect.left}px)` : "none",
                width: hoveredRect ? hoveredRect.width : 0,
                height: hoveredRect ? hoveredRect.height : 0,
                opacity: hoveredRect ? hoveredRect.opacity : 0,
              }}
            />

            {navLinks.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <a
                  key={href}
                  href={href}
                  className={`vt-link ${active ? "vt-link-active" : ""}`}
                  onMouseEnter={handleLinkMouseEnter}
                >
                  <Icon className="vt-link-icon" />
                  {label}
                  {active && <span className="vt-link-bar"></span>}
                </a>
              );
            })}
          </nav>

          {/* ── Right Cluster ─────────────────────────────────────────────── */}
          <div className="vt-right">

            {/* Health pill with active pulse ring */}
            <div className="vt-health" style={{ borderColor: `${statusColor}33` }}>
              <span className="vt-health-dot" style={{ background: statusColor, color: statusColor }}></span>
              <span className="vt-health-label" style={{ color: statusColor }}>{statusLabel}</span>
            </div>

            {/* Notification bell dropdown with tab filters */}
            {isLoggedIn && (
              <div className="vt-notif-wrap" ref={notifRef}>
                <button
                  className={`vt-bell-btn ${notifOpen ? "vt-bell-active" : ""} ${shouldShake ? "vt-bell-shake" : ""}`}
                  onClick={() => { setNotifOpen((o) => !o); if (!notifOpen) fetchNotifications(); }}
                  title="Notifications"
                >
                  <Bell className="vt-bell-icon" />
                  {unreadCount > 0 && (
                    <span className="vt-badge-count">{unreadCount > 9 ? "9+" : unreadCount}</span>
                  )}
                </button>

                {/* Dropdown Panel */}
                {notifOpen && (
                  <div className="vt-notif-panel">
                    <div className="vt-notif-header">
                      <div className="vt-notif-title">
                        <Bell style={{ width: 14, height: 14 }} />
                        Notifications
                        {unreadCount > 0 && <span className="vt-unread-chip">{unreadCount} new</span>}
                      </div>
                      {unreadCount > 0 && (
                        <button onClick={markAllRead} className="vt-mark-all-btn">
                          <CheckCheck style={{ width: 13, height: 13 }} /> Mark all
                        </button>
                      )}
                    </div>

                    {/* Filter Category Tabs */}
                    <div className="vt-notif-tabs">
                      {["all", "unread", "system", "escrow"].map((tab) => (
                        <button
                          key={tab}
                          className={`vt-notif-tab-btn ${notifTab === tab ? "vt-notif-tab-btn-active" : ""}`}
                          onClick={() => setNotifTab(tab)}
                        >
                          {tab}
                        </button>
                      ))}
                    </div>

                    <div className="vt-notif-list">
                      {filteredNotifs.length === 0 ? (
                        <div className="vt-notif-empty">
                          <Zap style={{ width: 24, height: 24, opacity: 0.3 }} />
                          <p>No notifications matching this filter.</p>
                        </div>
                      ) : (
                        filteredNotifs.map((n) => {
                          const cat   = (n.category || "SYSTEM").toUpperCase();
                          const style = CATEGORY_COLORS[cat] || CATEGORY_COLORS.SYSTEM;
                          const isUnread = !n.read_at;
                          const cta = getActionCTA(n);
                          return (
                            <div
                              key={n.id}
                              className={`vt-notif-item ${isUnread ? "vt-notif-unread" : ""}`}
                              onClick={() => isUnread && markRead(n.id)}
                            >
                              <div className="vt-notif-cat-dot" style={{ background: style.color }}></div>
                              <div className="vt-notif-body">
                                <div className="vt-notif-item-header">
                                  <span className="vt-notif-cat-chip" style={{ color: style.color, background: style.bg }}>
                                    {cat}
                                  </span>
                                  <span className="vt-notif-time">
                                    {new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                  </span>
                                </div>
                                <p className="vt-notif-item-title">{n.title}</p>
                                <p className="vt-notif-item-body">{n.body}</p>
                                
                                {/* Interactive contextual CTA links */}
                                {cta && (
                                  <a href={cta.href} className="vt-notif-cta-link" onClick={(e) => e.stopPropagation()}>
                                    {cta.label} &rarr;
                                  </a>
                                )}
                              </div>
                              {isUnread && (
                                <button
                                  className="vt-notif-read-btn"
                                  onClick={(e) => { e.stopPropagation(); markRead(n.id); }}
                                  disabled={markingId === n.id}
                                  title="Mark as read"
                                >
                                  <CheckCheck style={{ width: 12, height: 12 }} />
                                </button>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>

                    <div className="vt-notif-footer">
                      <a href="/notifications" className="vt-notif-view-all">View all notifications</a>
                      <span className="vt-notif-ws-label">
                        <span className="vt-ws-dot" style={{ background: wsRef.current?.readyState === 1 ? "#10b981" : "#64748b" }}></span>
                        Real-time active engine
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* User Pill and Interactive card panel */}
            {isLoggedIn ? (
              <div className="vt-user-wrapper" ref={userMenuRef}>
                <button
                  className={`vt-user-pill-btn ${userMenuOpen ? "vt-user-pill-active" : ""}`}
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                >
                  <span className="vt-user-avatar-wrap">
                    <span className="vt-user-avatar">
                      {(user?.email?.[0] || "U").toUpperCase()}
                    </span>
                    <span className={`vt-avatar-status-dot vt-avatar-status-${userStatus}`} />
                  </span>
                  <div className="vt-user-info">
                    <span className="vt-user-name">{user?.email?.split("@")[0] || "User"}</span>
                    {user?.role && <span className="vt-role-badge">{user.role}</span>}
                  </div>
                  <ChevronDown className="vt-user-chevron" />
                </button>

                {userMenuOpen && (
                  <div className="vt-user-dropdown">
                    <div className="vt-dropdown-header">
                      <span className="vt-dropdown-email">{user?.email}</span>
                      <span className="vt-dropdown-role">{user?.role || "GUEST"} ACCOUNT</span>
                    </div>
                    
                    {/* Interactive status toggles */}
                    <div className="vt-dropdown-divider"></div>
                    <div className="vt-user-status-selector">
                      {["online", "busy", "away"].map(status => (
                        <button
                          key={status}
                          className={`vt-status-selector-btn ${userStatus === status ? "vt-status-selector-btn-active" : ""}`}
                          onClick={() => setUserStatus(status)}
                        >
                          <span className="vt-status-bullet" data-status={status} />
                          {status}
                        </button>
                      ))}
                    </div>

                    {/* Role dashboard statistics card */}
                    <div className="vt-dropdown-divider"></div>
                    <div className="vt-user-dashboard-stats">
                      {user?.role === "TASKER" ? (
                        <>
                          <div className="vt-stat-row">
                            <span className="vt-stat-label">Work Score:</span>
                            <span className="vt-stat-value" style={{ color: "var(--color-teal)" }}>4.8 ★</span>
                          </div>
                          <div className="vt-stat-row">
                            <span className="vt-stat-label">Accepted Jobs:</span>
                            <span className="vt-stat-value">24 gigs</span>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="vt-stat-row">
                            <span className="vt-stat-label">Poster Rating:</span>
                            <span className="vt-stat-value" style={{ color: "var(--color-saffron)" }}>4.9 ★</span>
                          </div>
                          <div className="vt-stat-row">
                            <span className="vt-stat-label">Active Drafts:</span>
                            <span className="vt-stat-value">12 tasks</span>
                          </div>
                        </>
                      )}
                    </div>

                    <div className="vt-dropdown-divider"></div>
                    <a href="/my-tasks" className="vt-dropdown-item">
                      <LayoutDashboard style={{ width: 14, height: 14 }} />
                      My Tasks
                    </a>
                    <a href="/profile" className="vt-dropdown-item">
                      <User style={{ width: 14, height: 14 }} />
                      Profile
                    </a>
                    <a href="/poster" className="vt-dropdown-item">
                      <LayoutDashboard style={{ width: 14, height: 14 }} />
                      Poster Sandbox
                    </a>
                    <a href="/tasker" className="vt-dropdown-item">
                      <Radio style={{ width: 14, height: 14 }} />
                      Tasker Radar
                    </a>
                    <a href="/account" className="vt-dropdown-item">
                      <ShieldCheck style={{ width: 14, height: 14 }} />
                      Account & Email OTP
                    </a>
                    <a href="/notifications" className="vt-dropdown-item">
                      <Bell style={{ width: 14, height: 14 }} />
                      Notifications
                    </a>
                    <a href="/chat" className="vt-dropdown-item">
                      <MessageSquare style={{ width: 14, height: 14 }} />
                      AI Chat Agent
                    </a>
                    <a href="/verify" className="vt-dropdown-item">
                      <ShieldCheck style={{ width: 14, height: 14 }} />
                      Vision Proofs
                    </a>
                    <a href="/payments" className="vt-dropdown-item">
                      <CreditCard style={{ width: 14, height: 14 }} />
                      Ledger & Payments
                    </a>
                    <div className="vt-dropdown-divider"></div>
                    <button onClick={logout} className="vt-dropdown-item vt-dropdown-logout">
                      <LogOut style={{ width: 14, height: 14 }} />
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <a href="/login" className="btn-premium btn-teal vt-signin-btn">
                Sign In
              </a>
            )}

            {/* Mobile hamburger */}
            <button
              className="vt-hamburger"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X style={{ width: 20, height: 20 }} /> : <Menu style={{ width: 20, height: 20 }} />}
            </button>
          </div>
        </div>

        {/* ── Mobile Menu ─────────────────────────────────────────────────── */}
        {mobileOpen && (
          <div className="vt-mobile-menu">
            {navLinks.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <a key={href} href={href} className={`vt-mobile-link ${active ? "vt-mobile-link-active" : ""}`}>
                  <Icon style={{ width: 18, height: 18 }} />
                  {label}
                </a>
              );
            })}
            {!isLoggedIn && (
              <a href="/login" className="btn-premium btn-teal" style={{ width: "100%", marginTop: 8 }}>
                Sign In
              </a>
            )}
          </div>
        )}
      </header>

      {/* ── Advanced Keyboard Autocomplete Command Palette Overlay ────────── */}
      {paletteOpen && (
        <div className="vt-palette-overlay" onClick={() => setPaletteOpen(false)}>
          <div className="vt-palette-modal" onClick={(e) => e.stopPropagation()} ref={paletteRef}>
            <div className="vt-palette-search-wrapper">
              <Search className="vt-palette-search-icon" />
              <input
                id="vt-palette-input"
                type="text"
                className="vt-palette-input"
                placeholder="Search tools, view tasks feed, trigger actions..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setSelectedIdx(0); }}
                onKeyDown={handlePaletteKeyDown}
                autoComplete="off"
              />
              <span className="vt-palette-esc-badge">ESC</span>
            </div>

            <div className="vt-palette-results">
              {combinedPaletteItems.length === 0 ? (
                <div className="vt-palette-empty">
                  <Info style={{ width: 20, height: 20 }} />
                  <p>No results found for "{searchQuery}"</p>
                </div>
              ) : (
                Object.entries(
                  combinedPaletteItems.reduce((groups, item) => {
                    if (!groups[item.category]) groups[item.category] = [];
                    groups[item.category].push(item);
                    return groups;
                  }, {})
                ).map(([category, items]) => (
                  <div key={category} className="vt-palette-group">
                    <div className="vt-palette-group-title">{category}</div>
                    {items.map((item) => {
                      const indexInFiltered = combinedPaletteItems.indexOf(item);
                      const isSelected = indexInFiltered === selectedIdx;
                      const Icon = item.icon;
                      return (
                        <div
                          key={item.title}
                          className={`vt-palette-item ${isSelected ? "vt-palette-item-selected" : ""}`}
                          onClick={() => handlePaletteAction(item)}
                          onMouseEnter={() => setSelectedIdx(indexInFiltered)}
                        >
                          <Icon className="vt-palette-item-icon" />
                          <div className="vt-palette-item-info">
                            <div className="vt-palette-item-title">{item.title}</div>
                            <div className="vt-palette-item-subtitle">{item.subtitle}</div>
                          </div>
                          {isSelected && (
                            <span className="vt-palette-item-enter">
                              <CornerDownLeft style={{ width: 12, height: 12 }} />
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            <div className="vt-palette-footer">
              <span className="vt-palette-legend-item">
                <kbd>↑↓</kbd> Navigate
              </span>
              <span className="vt-palette-legend-item">
                <kbd>Enter</kbd> Select
              </span>
              <span className="vt-palette-legend-item">
                <kbd>Esc</kbd> Dismiss
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Styles ──────────────────────────────────────────────────────────── */}
      <style dangerouslySetInnerHTML={{ __html: `
        /* ── Vayu Top Glowing Accent line ── */
        .vt-top-accent {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          height: 2px;
          background: linear-gradient(90deg, var(--color-teal), #0d9488, var(--color-saffron), var(--color-teal));
          background-size: 300% 100%;
          z-index: 210;
          animation: vayuEnergyLine 6s linear infinite;
        }
        @keyframes vayuEnergyLine {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }

        /* ── Bell Shake micro-interaction ── */
        @keyframes bellShake {
          0% { transform: rotate(0); }
          15% { transform: rotate(15deg); }
          30% { transform: rotate(-15deg); }
          45% { transform: rotate(10deg); }
          60% { transform: rotate(-10deg); }
          75% { transform: rotate(5deg); }
          85% { transform: rotate(-5deg); }
          100% { transform: rotate(0); }
        }
        .vt-bell-shake {
          animation: bellShake 0.6s ease;
          border-color: var(--color-teal) !important;
          color: var(--color-teal) !important;
          box-shadow: 0 0 12px rgba(20, 184, 166, 0.25);
        }

        /* ── Dynamic Pulsing Waves for status indicator ── */
        .vt-health-dot {
          position: relative;
        }
        .vt-health-dot::after {
          content: '';
          position: absolute;
          top: -2px; left: -2px; right: -2px; bottom: -2px;
          border-radius: 50%;
          border: 1px solid currentColor;
          opacity: 0;
          transform: scale(1);
          animation: pulse-ring 2.2s cubic-bezier(0.24, 0, 0.38, 1) infinite;
        }
        @keyframes pulse-ring {
          0% { transform: scale(0.95); opacity: 0.85; }
          100% { transform: scale(2.8); opacity: 0; }
        }

        /* ── Sliding link highlight ── */
        .vt-links {
          position: relative;
          display: flex;
          align-items: center;
          gap: 4px;
          flex: 1;
          justify-content: center;
        }
        .vt-link-highlight {
          position: absolute;
          top: 0;
          left: 0;
          background: rgba(20, 184, 166, 0.08);
          border-radius: 8px;
          pointer-events: none;
          z-index: 0;
          transition: transform 0.22s cubic-bezier(0.25, 1, 0.5, 1),
                      width 0.22s cubic-bezier(0.25, 1, 0.5, 1),
                      opacity 0.15s ease;
        }

        /* ── Shell ── */
        .vt-nav {
          position: sticky;
          top: 0;
          left: 0;
          right: 0;
          z-index: 200;
          background: rgba(7, 9, 19, 0.75);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          border-bottom: 1px solid var(--border-glow);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .vt-nav-scrolled {
          background: rgba(5, 7, 16, 0.92);
          border-bottom: 1px solid rgba(20, 184, 166, 0.15);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(20, 184, 166, 0.05);
        }
        .vt-nav-inner {
          max-width: 1240px;
          margin: 0 auto;
          padding: 0 24px;
          height: 64px;
          display: flex;
          align-items: center;
          gap: 20px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .vt-nav-scrolled .vt-nav-inner {
          height: 52px;
        }

        /* ── Logo ── */
        .vt-logo {
          font-family: var(--font-heading);
          font-size: 1.25rem;
          font-weight: 800;
          color: var(--color-text-main);
          display: flex;
          align-items: center;
          gap: 8px;
          letter-spacing: -0.02em;
          flex-shrink: 0;
          text-decoration: none;
        }
        .vt-logo-dot {
          width: 9px; height: 9px;
          border-radius: 50%;
          background: var(--color-teal);
          box-shadow: 0 0 10px var(--color-teal);
          animation: pulse-glow-teal 2s infinite;
        }
        .vt-logo-badge {
          font-size: 0.65rem;
          padding: 2px 7px;
          border-radius: 6px;
          background: linear-gradient(135deg, var(--color-teal), #0d9488);
          color: #042f2e;
          font-weight: 800;
          letter-spacing: 0.05em;
        }

        /* ── Search Bar Trigger ── */
        .vt-search-trigger {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 7px 12px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-glow);
          border-radius: 8px;
          color: var(--color-text-muted);
          font-family: inherit;
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.2s ease;
          width: 170px;
          text-align: left;
        }
        .vt-search-trigger:hover {
          background: rgba(255, 255, 255, 0.07);
          border-color: rgba(20, 184, 166, 0.2);
          color: var(--color-text-main);
        }
        .vt-search-icon {
          width: 14px;
          height: 14px;
          flex-shrink: 0;
        }
        .vt-search-placeholder {
          flex: 1;
        }
        .vt-search-kbd {
          display: flex;
          align-items: center;
          gap: 3px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 1px 5px;
          border-radius: 4px;
          font-size: 0.65rem;
          font-weight: 600;
          font-family: monospace;
          color: var(--color-text-muted);
        }

        /* ── Nav Links ── */
        .vt-link {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 0.88rem;
          font-weight: 500;
          color: var(--color-text-muted);
          transition: all 0.2s ease;
          position: relative;
          white-space: nowrap;
          text-decoration: none;
          z-index: 1;
        }
        .vt-link:hover {
          color: var(--color-text-main);
        }
        .vt-link-active {
          color: var(--color-teal) !important;
          background: rgba(20,184,166,0.04) !important;
        }
        .vt-link-icon { width: 15px; height: 15px; flex-shrink: 0; }
        .vt-link-bar {
          position: absolute;
          bottom: -1px;
          left: 12px; right: 12px;
          height: 2px;
          background: var(--color-teal);
          border-radius: 2px;
          box-shadow: 0 0 8px var(--color-teal);
        }

        /* ── Right Cluster ── */
        .vt-right {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-shrink: 0;
        }

        /* ── Health ── */
        .vt-health {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 5px 10px;
          border-radius: 20px;
          background: rgba(255,255,255,0.02);
          border-width: 1px;
          border-style: solid;
          transition: all 0.3s ease;
        }
        .vt-nav-scrolled .vt-health {
          padding: 4px 8px;
        }
        .vt-health-dot {
          width: 7px; height: 7px;
          border-radius: 50%;
          transition: all 0.3s ease;
          flex-shrink: 0;
        }
        .vt-health-label {
          font-size: 0.72rem;
          font-weight: 600;
          white-space: nowrap;
        }

        /* ── Notification Bell ── */
        .vt-notif-wrap { position: relative; }
        .vt-bell-btn {
          position: relative;
          width: 38px; height: 38px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid var(--border-glow);
          color: var(--color-text-muted);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .vt-nav-scrolled .vt-bell-btn {
          width: 34px; height: 34px;
        }
        .vt-bell-btn:hover, .vt-bell-active {
          color: var(--color-text-main);
          background: rgba(20,184,166,0.08);
          border-color: var(--border-teal);
        }
        .vt-bell-icon { width: 17px; height: 17px; }
        .vt-badge-count {
          position: absolute;
          top: -5px; right: -5px;
          min-width: 18px; height: 18px;
          border-radius: 9px;
          background: linear-gradient(135deg, #ef4444, #dc2626);
          color: white;
          font-size: 0.62rem;
          font-weight: 800;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0 4px;
          border: 2px solid rgba(7,9,19,1);
          animation: pulse-glow-saffron 2s infinite;
        }

        /* ── Notification Panel ── */
        .vt-notif-panel {
          position: absolute;
          top: calc(100% + 10px);
          right: 0;
          width: 360px;
          background: rgba(11, 15, 25, 0.98);
          backdrop-filter: blur(20px);
          border: 1px solid var(--border-glow);
          border-radius: 16px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(20,184,166,0.05);
          overflow: hidden;
          animation: dropIn 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          z-index: 300;
        }
        @keyframes dropIn {
          from { opacity: 0; transform: translateY(-8px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        .vt-notif-header {
          padding: 16px 18px 12px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid var(--border-glow);
        }
        .vt-notif-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.9rem;
          font-weight: 700;
          color: var(--color-text-main);
        }
        .vt-unread-chip {
          font-size: 0.65rem;
          padding: 2px 7px;
          border-radius: 10px;
          background: rgba(239,68,68,0.12);
          border: 1px solid rgba(239,68,68,0.25);
          color: #f87171;
          font-weight: 700;
        }
        .vt-mark-all-btn {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 0.72rem;
          font-weight: 600;
          color: var(--color-teal);
          background: transparent;
          border: none;
          cursor: pointer;
          font-family: inherit;
          padding: 4px 8px;
          border-radius: 6px;
          transition: background 0.15s ease;
        }
        .vt-mark-all-btn:hover { background: rgba(20,184,166,0.08); }

        /* Notification tabs chips */
        .vt-notif-tabs {
          display: flex;
          gap: 6px;
          padding: 8px 16px;
          background: rgba(0, 0, 0, 0.15);
          border-bottom: 1px solid var(--border-glow);
        }
        .vt-notif-tab-btn {
          background: transparent;
          border: none;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.68rem;
          text-transform: capitalize;
          color: var(--color-text-muted);
          cursor: pointer;
          transition: all 0.18s;
          font-family: inherit;
          font-weight: 600;
        }
        .vt-notif-tab-btn:hover {
          color: var(--color-text-main);
          background: rgba(255, 255, 255, 0.04);
        }
        .vt-notif-tab-btn-active {
          color: var(--color-teal) !important;
          background: rgba(20, 184, 166, 0.08) !important;
          border: 1px solid rgba(20, 184, 166, 0.15);
        }

        .vt-notif-list {
          max-height: 300px;
          overflow-y: auto;
        }
        .vt-notif-list::-webkit-scrollbar { width: 3px; }
        .vt-notif-list::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 2px; }

        .vt-notif-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 36px 20px;
          color: var(--color-text-muted);
          text-align: center;
        }
        .vt-notif-empty p { font-size: 0.8rem; }

        .vt-notif-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 13px 16px;
          border-bottom: 1px solid var(--border-glow);
          cursor: pointer;
          transition: background 0.15s ease;
          position: relative;
        }
        .vt-notif-item:last-child { border-bottom: none; }
        .vt-notif-item:hover { background: rgba(255,255,255,0.02); }
        .vt-notif-unread { background: rgba(20,184,166,0.02); }
        .vt-notif-cat-dot {
          width: 8px; height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
          margin-top: 5px;
        }
        .vt-notif-body { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
        .vt-notif-item-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .vt-notif-cat-chip {
          font-size: 0.62rem;
          font-weight: 700;
          padding: 2px 7px;
          border-radius: 8px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .vt-notif-time {
          font-size: 0.68rem;
          color: var(--color-text-muted);
          white-space: nowrap;
        }
        .vt-notif-item-title {
          font-size: 0.83rem;
          font-weight: 700;
          color: var(--color-text-main);
          line-height: 1.3;
        }
        .vt-notif-item-body {
          font-size: 0.77rem;
          color: var(--color-text-muted);
          line-height: 1.4;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .vt-notif-cta-link {
          font-size: 0.72rem;
          font-weight: 700;
          color: var(--color-teal);
          text-decoration: none;
          align-self: flex-start;
          margin-top: 4px;
          padding: 2px 6px;
          background: rgba(20, 184, 166, 0.08);
          border-radius: 4px;
          transition: background 0.15s;
        }
        .vt-notif-cta-link:hover {
          background: rgba(20, 184, 166, 0.15);
        }

        .vt-notif-read-btn {
          width: 26px; height: 26px;
          border-radius: 6px;
          background: rgba(20,184,166,0.07);
          border: 1px solid var(--border-teal);
          color: var(--color-teal);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          flex-shrink: 0;
          transition: all 0.15s ease;
        }
        .vt-notif-read-btn:hover { background: rgba(20,184,166,0.15); }

        .vt-notif-footer {
          padding: 10px 16px;
          border-top: 1px solid var(--border-glow);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .vt-notif-view-all {
          font-size: 0.72rem;
          font-weight: 700;
          color: var(--color-teal);
          text-decoration: none;
        }
        .vt-notif-view-all:hover { text-decoration: underline; }
        .vt-notif-ws-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.7rem;
          color: var(--color-text-muted);
        }
        .vt-ws-dot {
          width: 6px; height: 6px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        /* ── User wrapper ── */
        .vt-user-wrapper {
          position: relative;
        }
        .vt-user-pill-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 10px 4px 4px;
          background: rgba(20, 184, 166, 0.05);
          border: 1px solid var(--border-teal);
          border-radius: 20px;
          cursor: pointer;
          transition: all 0.25s ease;
          color: var(--color-text-main);
          font-family: inherit;
        }
        .vt-user-pill-btn:hover, .vt-user-pill-active {
          background: rgba(20, 184, 166, 0.1);
          border-color: var(--color-teal);
          box-shadow: 0 0 10px rgba(20, 184, 166, 0.15);
        }
        
        .vt-user-avatar-wrap {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .vt-user-avatar {
          width: 26px; height: 26px;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--color-teal), #0d9488);
          color: #042f2e;
          font-size: 0.75rem;
          font-weight: 800;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .vt-avatar-status-dot {
          position: absolute;
          bottom: -2px; right: -2px;
          width: 8px; height: 8px;
          border-radius: 50%;
          border: 1.5px solid rgba(7, 9, 19, 1);
        }
        .vt-avatar-status-online { background: #10b981; }
        .vt-avatar-status-busy   { background: #ef4444; }
        .vt-avatar-status-away   { background: #f59e0b; }

        .vt-user-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 1px;
          line-height: 1;
        }
        .vt-user-name {
          font-size: 0.8rem;
          font-weight: 700;
          color: var(--color-text-main);
          max-width: 90px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .vt-role-badge {
          font-size: 0.55rem;
          font-weight: 700;
          padding: 1px 4px;
          border-radius: 4px;
          background: rgba(245,158,11,0.1);
          color: var(--color-saffron);
          border: 1px solid var(--border-saffron);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .vt-user-chevron {
          color: var(--color-text-muted);
          transition: transform 0.2s ease;
          width: 14px;
          height: 14px;
        }
        .vt-user-pill-active .vt-user-chevron {
          transform: rotate(180deg);
          color: var(--color-text-main);
        }

        .vt-user-dropdown {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          width: 232px;
          background: rgba(11, 15, 25, 0.98);
          backdrop-filter: blur(24px);
          border: 1px solid var(--border-glow);
          border-radius: 12px;
          box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05);
          padding: 8px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          z-index: 300;
          animation: dropIn 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .vt-dropdown-header {
          padding: 8px 10px;
          display: flex;
          flex-direction: column;
          gap: 3px;
        }
        .vt-dropdown-email {
          font-size: 0.78rem;
          color: var(--color-text-main);
          font-weight: 600;
          word-break: break-all;
        }
        .vt-dropdown-role {
          font-size: 0.6rem;
          color: var(--color-text-muted);
          font-weight: 800;
          letter-spacing: 0.05em;
        }
        .vt-dropdown-divider {
          height: 1px;
          background: var(--border-glow);
          margin: 4px 0;
        }

        /* Status selector buttons */
        .vt-user-status-selector {
          display: flex;
          gap: 4px;
          padding: 4px;
          background: rgba(0, 0, 0, 0.25);
          border-radius: 8px;
        }
        .vt-status-selector-btn {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 5px;
          background: transparent;
          border: none;
          border-radius: 6px;
          font-size: 0.62rem;
          font-weight: 700;
          color: var(--color-text-muted);
          padding: 4px 0;
          cursor: pointer;
          font-family: inherit;
          text-transform: uppercase;
          transition: all 0.15s;
        }
        .vt-status-selector-btn:hover {
          color: var(--color-text-main);
          background: rgba(255, 255, 255, 0.03);
        }
        .vt-status-selector-btn-active {
          color: var(--color-text-main) !important;
          background: rgba(255, 255, 255, 0.08) !important;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }
        .vt-status-bullet {
          width: 5px; height: 5px;
          border-radius: 50%;
        }
        .vt-status-bullet[data-status="online"] { background: #10b981; }
        .vt-status-bullet[data-status="busy"]   { background: #ef4444; }
        .vt-status-bullet[data-status="away"]   { background: #f59e0b; }

        /* User ratings metrics card */
        .vt-user-dashboard-stats {
          background: rgba(20, 184, 166, 0.02);
          border: 1px solid rgba(20, 184, 166, 0.06);
          border-radius: 8px;
          padding: 8px 10px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .vt-stat-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 0.68rem;
          font-weight: 600;
        }
        .vt-stat-label {
          color: var(--color-text-muted);
        }
        .vt-stat-value {
          color: var(--color-text-main);
          font-weight: 700;
        }

        .vt-dropdown-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 6px;
          font-size: 0.8rem;
          color: var(--color-text-muted);
          text-decoration: none;
          transition: all 0.15s ease;
          background: transparent;
          border: none;
          cursor: pointer;
          width: 100%;
          text-align: left;
          font-family: inherit;
        }
        .vt-dropdown-item:hover {
          color: var(--color-text-main);
          background: rgba(255, 255, 255, 0.04);
        }
        .vt-dropdown-logout {
          color: #f87171;
        }
        .vt-dropdown-logout:hover {
          color: #ef4444;
          background: rgba(239, 68, 68, 0.08);
        }

        .vt-signin-btn { padding: 8px 18px; font-size: 0.85rem; }

        /* ── Command Palette overlay & modal ── */
        .vt-palette-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(3, 4, 8, 0.65);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          z-index: 500;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding: 80px 16px 20px;
          animation: fadeOverlay 0.15s ease-out;
        }
        @keyframes fadeOverlay {
          from { opacity: 0; }
          to   { opacity: 1; }
        }

        .vt-palette-modal {
          width: 100%;
          max-width: 580px;
          background: rgba(11, 15, 25, 0.95);
          backdrop-filter: blur(24px);
          -webkit-backdrop-filter: blur(24px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          box-shadow: 0 30px 90px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(20, 184, 166, 0.05);
          overflow: hidden;
          display: flex;
          flex-direction: column;
          animation: popPalette 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes popPalette {
          from { transform: scale(0.95) translateY(-10px); }
          to   { transform: scale(1) translateY(0); }
        }

        .vt-palette-search-wrapper {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          position: relative;
        }
        .vt-palette-search-icon {
          width: 18px; height: 18px;
          color: var(--color-teal);
        }
        .vt-palette-input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: var(--color-text-main);
          font-family: inherit;
          font-size: 0.95rem;
        }
        .vt-palette-input::placeholder {
          color: var(--color-text-muted);
        }
        .vt-palette-esc-badge {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.05);
          color: var(--color-text-muted);
          font-size: 0.62rem;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: monospace;
        }

        .vt-palette-results {
          max-height: 380px;
          overflow-y: auto;
          padding: 10px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .vt-palette-results::-webkit-scrollbar { width: 3px; }
        .vt-palette-results::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 2px; }

        .vt-palette-empty {
          padding: 40px 20px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          color: var(--color-text-muted);
          text-align: center;
        }
        .vt-palette-empty p { font-size: 0.85rem; }

        .vt-palette-group-title {
          font-size: 0.65rem;
          font-weight: 800;
          color: var(--color-text-muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          padding: 8px 12px 4px;
        }

        .vt-palette-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .vt-palette-item-selected {
          background: rgba(20, 184, 166, 0.08);
          border-left: 3px solid var(--color-teal);
          padding-left: 9px;
        }
        .vt-palette-item-icon {
          width: 16px; height: 16px;
          color: var(--color-text-muted);
          transition: color 0.15s ease;
        }
        .vt-palette-item-selected .vt-palette-item-icon {
          color: var(--color-teal);
        }
        .vt-palette-item-info {
          flex: 1;
          display: flex;
          flex-direction: column;
        }
        .vt-palette-item-title {
          font-size: 0.85rem;
          font-weight: 700;
          color: var(--color-text-main);
        }
        .vt-palette-item-subtitle {
          font-size: 0.73rem;
          color: var(--color-text-muted);
        }
        .vt-palette-item-enter {
          color: var(--color-teal);
          animation: breathe 1.5s infinite alternate;
        }

        .vt-palette-footer {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 12px 16px;
          background: rgba(0, 0, 0, 0.2);
          border-top: 1px solid rgba(255, 255, 255, 0.04);
        }
        .vt-palette-legend-item {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.68rem;
          color: var(--color-text-muted);
        }
        .vt-palette-legend-item kbd {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 1px 4px;
          border-radius: 3px;
          font-family: monospace;
          color: var(--color-text-main);
        }

        /* ── Hamburger ── */
        .vt-hamburger {
          display: none;
          width: 36px; height: 36px;
          border-radius: 8px;
          background: rgba(255,255,255,0.04);
          border: 1px solid var(--border-glow);
          color: var(--color-text-main);
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: background 0.2s ease;
        }
        .vt-hamburger:hover { background: rgba(255,255,255,0.08); }

        /* ── Mobile menu ── */
        .vt-mobile-menu {
          display: none;
          flex-direction: column;
          gap: 4px;
          padding: 12px 20px 16px;
          border-top: 1px solid var(--border-glow);
          animation: dropIn 0.18s ease;
        }
        .vt-mobile-link {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 11px 14px;
          border-radius: 10px;
          font-size: 0.92rem;
          font-weight: 500;
          color: var(--color-text-muted);
          transition: all 0.15s ease;
          text-decoration: none;
        }
        .vt-mobile-link:hover { background: rgba(255,255,255,0.04); color: var(--color-text-main); }
        .vt-mobile-link-active { color: var(--color-teal) !important; background: rgba(20,184,166,0.07) !important; }

        /* ── Responsive ── */
        @media (max-width: 960px) {
          .vt-links { display: none; }
          .vt-health { display: none; }
          .vt-hamburger { display: flex; }
          .vt-mobile-menu { display: flex; }
          .vt-search-trigger { width: 120px; }
          .vt-search-kbd { display: none; }
        }
        @media (max-width: 480px) {
          .vt-user-info { display: none; }
          .vt-user-pill-btn { padding: 4px; border-radius: 50%; }
          .vt-user-chevron { display: none; }
          .vt-search-trigger { width: 40px; padding: 7px; justify-content: center; }
          .vt-search-placeholder { display: none; }
        }
      ` }} />
    </>
  );
}

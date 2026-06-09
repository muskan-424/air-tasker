/** Shared notification helpers for NavBar and /notifications page. */

export const CATEGORY_COLORS = {
  TASK: { color: "#14b8a6", bg: "rgba(20,184,166,0.1)" },
  ESCROW: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  DISPUTE: { color: "#f87171", bg: "rgba(248,113,113,0.1)" },
  SYSTEM: { color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
};

/** Normalize REST list item or WebSocket envelope into one shape. */
export function normalizeNotification(raw) {
  if (!raw) return null;
  const data = raw.data && raw.type === "notification" ? raw.data : raw;
  const payload = data.payload || null;
  return {
    id: data.id,
    title: data.title || "",
    body: data.body || "",
    category: (data.category || "SYSTEM").toUpperCase(),
    payload,
    task_id: payload?.task_id || data.task_id || null,
    read_at: data.read_at || null,
    delivery_status: data.delivery_status || "delivered",
    created_at: data.created_at || new Date().toISOString(),
  };
}

export function getNotificationAction(n) {
  const cat = (n.category || "").toUpperCase();
  const taskId = n.task_id || n.payload?.task_id;
  if (cat === "ESCROW" && taskId) {
    return { label: "Open Payments", href: `/payments?task_id=${taskId}` };
  }
  if (cat === "TASK" && taskId) {
    return { label: "View Task", href: `/tasks/${taskId}` };
  }
  if (cat === "TASK") {
    return { label: "Tasker Radar", href: "/tasker" };
  }
  if (cat === "DISPUTE" && taskId) {
    return { label: "Verify / Dispute", href: `/verify?task_id=${taskId}` };
  }
  if (cat === "DISPUTE") {
    return { label: "AI Chat", href: "/chat" };
  }
  return null;
}

export function filterNotifications(notifications, tab) {
  return notifications.filter((n) => {
    if (tab === "unread") return !n.read_at;
    if (tab === "system") return (n.category || "").toUpperCase() === "SYSTEM";
    if (tab === "escrow") return (n.category || "").toUpperCase() === "ESCROW";
    if (tab === "task") return (n.category || "").toUpperCase() === "TASK";
    return true;
  });
}

export function formatNotificationTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now - d;
  if (diffMs < 60000) return "Just now";
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

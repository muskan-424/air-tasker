/**
 * Centralized API client for VayuTask AI.
 * Automatically attaches JWT from localStorage and handles auth errors.
 *
 * When NEXT_PUBLIC_API_BASE is empty, requests use same-origin /api/* and
 * Next.js rewrites proxy to the FastAPI backend (see next.config.mjs).
 */

import { API_BASE, WS_BASE } from "./env";

const BACKEND_BASE = API_BASE;

/**
 * Core fetch wrapper — auto-attaches Authorization header, returns parsed JSON.
 * @param {string} path - e.g. "/api/auth/login"
 * @param {RequestInit} options - standard fetch options
 * @param {string|null} tokenOverride - optional token override (for auth calls)
 */
export async function apiFetch(path, options = {}, tokenOverride = null) {
  const token =
    tokenOverride ||
    (typeof window !== "undefined" ? localStorage.getItem("vayutask_token") : null);

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BACKEND_BASE}${path}`, {
    ...options,
    headers,
  });

  // Handle 401 — clear token and redirect to login
  if (response.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("vayutask_token");
      localStorage.removeItem("vayutask_user");
      window.location.href = "/login";
    }
    throw new Error("Unauthorized — please log in again.");
  }

  // For non-2xx responses, throw with body detail
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      detail = err.detail || err.message || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  // Return parsed JSON
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export const authAPI = {
  register: (email, password, role = "POSTER") =>
    apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, role }),
    }),

  login: (email, password) =>
    apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
};

// ─── Task Drafts ─────────────────────────────────────────────────────────────

export const draftsAPI = {
  create: (rawInput, language = "en") =>
    apiFetch("/api/tasks/drafts", {
      method: "POST",
      body: JSON.stringify({ raw_input: rawInput, language }),
    }),

  get: (draftId) => apiFetch(`/api/tasks/drafts/${draftId}`),

  update: (draftId, aiSchema) =>
    apiFetch(`/api/tasks/drafts/${draftId}`, {
      method: "PATCH",
      body: JSON.stringify({ ai_schema: aiSchema }),
    }),
};

// ─── Tasks ───────────────────────────────────────────────────────────────────

export const tasksAPI = {
  publish: (draftId) =>
    apiFetch(`/api/tasks/${draftId}/publish`, { method: "POST" }),

  feed: (category = null, limit = 20) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (category) params.set("category", category);
    return apiFetch(`/api/tasks/feed?${params.toString()}`);
  },

  mine: (limit = 20) => apiFetch(`/api/tasks/mine?limit=${limit}`),

  get: (taskId) => apiFetch(`/api/tasks/${taskId}`),

  accept: (taskId, acknowledgement = "I acknowledge the requirements.") =>
    apiFetch(`/api/tasks/${taskId}/accept`, {
      method: "POST",
      body: JSON.stringify({
        acknowledge_requirements: true,
        acknowledgement,
      }),
    }),

  uploadEvidence: (taskId, beforeImageUrl, afterImageUrl, evidenceVideoUrl = null) =>
    apiFetch(`/api/tasks/${taskId}/evidence`, {
      method: "POST",
      body: JSON.stringify({
        before_image_url: beforeImageUrl,
        after_image_url: afterImageUrl,
        evidence_video_url: evidenceVideoUrl,
      }),
    }),

  verify: (taskId) =>
    apiFetch(`/api/tasks/${taskId}/verify`, { method: "POST" }),

  startEscrow: (taskId) =>
    apiFetch(`/api/tasks/${taskId}/escrow/start`, { method: "POST" }),

  releaseEscrow: (taskId) =>
    apiFetch(`/api/tasks/${taskId}/escrow/release`, { method: "POST" }),
};

// ─── Payments ────────────────────────────────────────────────────────────────

export const paymentsAPI = {
  createRazorpayOrder: (taskId) =>
    apiFetch("/api/payments/razorpay/order", {
      method: "POST",
      body: JSON.stringify({ task_id: taskId }),
    }),
};

// ─── Chat ────────────────────────────────────────────────────────────────────

export const chatAPI = {
  translate: (text, targetLang = "hi", sourceLang = "auto") =>
    apiFetch("/api/chat/translate", {
      method: "POST",
      body: JSON.stringify({ text, source_lang: sourceLang, target_lang: targetLang }),
    }),

  agent: (message, sessionId = null, language = "en", tone = "friendly") =>
    apiFetch("/api/chat/agent", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId, language, tone }),
    }),

  refine: (originalAnswer, instruction, language = "en") =>
    apiFetch("/api/chat/refine", {
      method: "POST",
      body: JSON.stringify({
        original_answer: originalAnswer,
        instruction,
        language,
      }),
    }),

  history: (sessionId) => apiFetch(`/api/chat/history/${sessionId}`),

  /** Build authenticated WebSocket URL pointing to backend directly */
  buildWsUrl: (token) => `${WS_BASE}/api/chat/ws?token=${token}`,
};

// ─── Notifications ───────────────────────────────────────────────────────────

export const notificationsAPI = {
  list: (limit = 20) => apiFetch(`/api/notifications?limit=${limit}`),

  markRead: (notificationId) =>
    apiFetch(`/api/notifications/${notificationId}/read`, { method: "PATCH" }),

  /** Build authenticated WebSocket URL for real-time push notifications */
  buildWsUrl: (token) => `${WS_BASE}/api/notifications/ws?token=${token}`,
};

// ─── Health ──────────────────────────────────────────────────────────────────

export const healthAPI = {
  check: () => apiFetch("/api/health"),
};

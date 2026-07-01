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

  feed: (category = null, limit = 20, pin = null) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (category) params.set("category", category);
    if (pin) params.set("pin", pin);
    return apiFetch(`/api/tasks/feed?${params.toString()}`);
  },

  mine: (limit = 20) => apiFetch(`/api/tasks/mine?limit=${limit}`),

  get: (taskId) => apiFetch(`/api/tasks/${taskId}`),

  accept: (taskId, acknowledgement = { confirmed: true }) =>
    apiFetch(`/api/tasks/${taskId}/accept`, {
      method: "POST",
      body: JSON.stringify({
        acknowledge_requirements: true,
        acknowledgement:
          typeof acknowledgement === "object" && acknowledgement !== null
            ? acknowledgement
            : { note: String(acknowledgement) },
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

  getEvidence: (taskId) => apiFetch(`/api/tasks/${taskId}/evidence`),

  startEscrow: (taskId) =>
    apiFetch(`/api/tasks/${taskId}/escrow/start`, { method: "POST" }),

  releaseEscrow: (taskId) =>
    apiFetch(`/api/tasks/${taskId}/escrow/release`, { method: "POST" }),

  rate: (taskId, score, comment = null) =>
    apiFetch(`/api/tasks/${taskId}/rate`, {
      method: "POST",
      body: JSON.stringify({ score, comment }),
    }),

  getMyRating: (taskId) => apiFetch(`/api/tasks/${taskId}/rating`),

  listDisputes: (taskId) => apiFetch(`/api/tasks/${taskId}/disputes`),

  openDispute: (taskId, reason = null) =>
    apiFetch(`/api/tasks/${taskId}/disputes`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  listOpenDisputes: () => apiFetch("/api/tasks/disputes/open"),

  listReviewVerifications: () => apiFetch("/api/tasks/admin/verifications/review"),

  resolveDispute: (disputeId, outcome = "release", note = null) =>
    apiFetch(`/api/tasks/disputes/${disputeId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ outcome, note }),
    }),
};

// ─── Reports & trust ─────────────────────────────────────────────────────────

export const reportsAPI = {
  create: ({ reportedUserId, taskId, category, reason }) =>
    apiFetch("/api/reports", {
      method: "POST",
      body: JSON.stringify({
        reported_user_id: reportedUserId || null,
        task_id: taskId || null,
        category: category || "other",
        reason,
      }),
    }),

  listOpen: () => apiFetch("/api/reports/open"),

  resolve: (reportId, outcome, adminNotes = null) =>
    apiFetch(`/api/reports/${reportId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ outcome, admin_notes: adminNotes }),
    }),

  listTrustFlags: () => apiFetch("/api/reports/trust-flags/active"),
};

// ─── Payments ────────────────────────────────────────────────────────────────

export const paymentsAPI = {
  createRazorpayOrder: (taskId) =>
    apiFetch("/api/payments/razorpay/order", {
      method: "POST",
      body: JSON.stringify({ task_id: taskId }),
    }),

  payoutStatus: () => apiFetch("/api/payments/razorpay/payout/status"),

  registerPayoutBank: (beneficiaryName, ifsc, accountNumber) =>
    apiFetch("/api/payments/razorpay/payout/register-bank", {
      method: "POST",
      body: JSON.stringify({
        beneficiary_name: beneficiaryName,
        ifsc,
        account_number: accountNumber,
      }),
    }),
};

// ─── KYC ─────────────────────────────────────────────────────────────────────

export const kycAPI = {
  status: () => apiFetch("/api/kyc/me"),

  submit: (fullName, pan, aadhaarLast4 = null) =>
    apiFetch("/api/kyc/submit", {
      method: "POST",
      body: JSON.stringify({
        full_name: fullName,
        pan,
        aadhaar_last4: aadhaarLast4 || null,
      }),
    }),

  listPending: () => apiFetch("/api/kyc/admin/pending"),

  review: (userId, decision, reason = null) =>
    apiFetch(`/api/kyc/admin/${userId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, reason }),
    }),
};

// ─── Uploads ─────────────────────────────────────────────────────────────────

export const uploadsAPI = {
  /** POST /api/uploads/evidence — store file locally, returns { url }. */
  uploadEvidenceFile: async (file) => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("vayutask_token") : null;
    const form = new FormData();
    form.append("file", file);

    const response = await fetch(`${BACKEND_BASE}/api/uploads/evidence`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });

    if (response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("vayutask_token");
        localStorage.removeItem("vayutask_user");
        window.location.href = "/login";
      }
      throw new Error("Unauthorized — please log in again.");
    }

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        detail = err.detail || err.message || detail;
      } catch (_) {}
      throw new Error(detail);
    }

    return response.json();
  },
};

/** Resolve relative upload URLs for img src (works with Next.js /api rewrite). */
export function resolveMediaUrl(url) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("blob:")) {
    return url;
  }
  return `${BACKEND_BASE}${url.startsWith("/") ? url : `/${url}`}`;
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

// ─── User Profile ────────────────────────────────────────────────────────────

export const profileAPI = {
  get: () => apiFetch("/api/users/me/profile"),

  update: (payload) =>
    apiFetch("/api/users/me/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  ratingsSummary: (userId) => apiFetch(`/api/users/${userId}/ratings-summary`),
};

// ─── Account & OTP ───────────────────────────────────────────────────────────

export const accountAPI = {
  me: () => apiFetch("/api/users/me"),
};

export const verificationAPI = {
  requestEmailOtp: (purpose = "EMAIL_VERIFICATION") =>
    apiFetch("/api/verification/email/request-otp", {
      method: "POST",
      body: JSON.stringify({ purpose }),
    }),

  verifyEmailOtp: (code, purpose = "EMAIL_VERIFICATION") =>
    apiFetch("/api/verification/email/verify", {
      method: "POST",
      body: JSON.stringify({ purpose, code }),
    }),
};

// ─── Voice ───────────────────────────────────────────────────────────────────

export const voiceAPI = {
  /** Upload audio blob to POST /api/voice/transcribe (multipart). */
  transcribe: async (audioBlob, languageHint = "auto") => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("vayutask_token") : null;
    const form = new FormData();
    form.append("file", audioBlob, "recording.webm");

    const params = new URLSearchParams({ language_hint: languageHint });
    const response = await fetch(`${BACKEND_BASE}/api/voice/transcribe?${params}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });

    if (response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("vayutask_token");
        localStorage.removeItem("vayutask_user");
        window.location.href = "/login";
      }
      throw new Error("Unauthorized — please log in again.");
    }

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        detail = err.detail || err.message || detail;
      } catch (_) {}
      throw new Error(detail);
    }

    return response.json();
  },
};

// ─── Notifications ───────────────────────────────────────────────────────────

export const notificationsAPI = {
  list: (limit = 20) => apiFetch(`/api/notifications?limit=${limit}`),

  markRead: (notificationId) =>
    apiFetch(`/api/notifications/${notificationId}/read`, { method: "PATCH" }),

  getPreferences: () => apiFetch("/api/notifications/preferences"),

  updatePreferences: (payload) =>
    apiFetch("/api/notifications/preferences", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  /** Build authenticated WebSocket URL for real-time push notifications */
  buildWsUrl: (token) => `${WS_BASE}/api/notifications/ws?token=${token}`,
};

// ─── Health ──────────────────────────────────────────────────────────────────

export const healthAPI = {
  check: () => apiFetch("/api/health"),
  capabilities: () => apiFetch("/api/health/capabilities"),
};

// ─── Closed beta ─────────────────────────────────────────────────────────────

export const betaAPI = {
  getConfig: () => apiFetch("/api/beta/config"),
  submitFeedback: (payload) =>
    apiFetch("/api/beta/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getKpis: () => apiFetch("/api/beta/kpis"),
};

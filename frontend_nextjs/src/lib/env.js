/**
 * Public env helpers for VayuTask AI (Next.js).
 * Only NEXT_PUBLIC_* vars are available in the browser.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE?.replace(/\/$/, "") || "ws://localhost:4000";

export const APP_NAME = "VayuTask AI";

/**
 * Log dev-time hints when env is misconfigured.
 * Call once from a client component on mount.
 */
export function validatePublicEnv() {
  if (typeof window === "undefined") return;
  if (process.env.NODE_ENV !== "development") return;

  if (API_BASE && !process.env.NEXT_PUBLIC_WS_BASE) {
    console.warn(
      `[${APP_NAME}] NEXT_PUBLIC_API_BASE is set but NEXT_PUBLIC_WS_BASE is not. ` +
        "WebSockets default to ws://localhost:4000 — set NEXT_PUBLIC_WS_BASE if your API is elsewhere."
    );
  }

  if (!API_BASE) {
    console.info(
      `[${APP_NAME}] Using same-origin /api/* (Next.js rewrite to backend). ` +
        "Ensure the API is running on port 4000 or set NEXT_PUBLIC_API_REWRITE_TARGET."
    );
  }
}

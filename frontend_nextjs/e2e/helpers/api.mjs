/** API helpers for Playwright E2E — hit FastAPI directly for setup and assertions. */

const API_BASE = process.env.PLAYWRIGHT_API_BASE || "http://localhost:4000";

const DEFAULT_PASSWORD = "TestPass123!";

export function uniqueEmail(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@example.com`;
}

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

export async function registerUser(request, { email, password = DEFAULT_PASSWORD, role }) {
  const res = await request.post(`${API_BASE}/api/auth/register`, {
    data: { email, password, role },
  });
  if (!res.ok()) {
    throw new Error(`register ${role} failed (${res.status()}): ${await res.text()}`);
  }
  const { access_token: token } = await res.json();
  return { email, password, token, role };
}

export async function loginSession(page, { token, email, role }) {
  const payload = JSON.parse(
    Buffer.from(token.split(".")[1], "base64url").toString("utf8")
  );
  const user = { email, role, id: payload.sub };
  await page.goto("/");
  await page.evaluate(
    ({ token: t, user: u }) => {
      localStorage.setItem("vayutask_token", t);
      localStorage.setItem("vayutask_user", JSON.stringify(u));
    },
    { token, user }
  );
  await page.reload();
  await page.waitForFunction(() => localStorage.getItem("vayutask_token"));
}

export async function createPublishedTask(request, posterToken, rawInput) {
  const headers = authHeaders(posterToken);
  const draftRes = await request.post(`${API_BASE}/api/tasks/drafts`, {
    headers,
    data: {
      raw_input:
        rawInput ||
        "E2E test: electrical wiring repair in Dehradun PIN 248001, quick turnaround, budget up to 2000 INR",
      language: "en",
    },
  });
  if (!draftRes.ok()) {
    throw new Error(`draft failed (${draftRes.status()}): ${await draftRes.text()}`);
  }
  const draftId = (await draftRes.json()).id;

  const publishRes = await request.post(`${API_BASE}/api/tasks/${draftId}/publish`, {
    headers,
  });
  if (!publishRes.ok()) {
    throw new Error(`publish failed (${publishRes.status()}): ${await publishRes.text()}`);
  }
  return (await publishRes.json()).id;
}

export async function acceptTask(request, taskerToken, taskId) {
  const res = await request.post(`${API_BASE}/api/tasks/${taskId}/accept`, {
    headers: authHeaders(taskerToken),
    data: { acknowledge_requirements: true, acknowledgement: { gear: "yes" } },
  });
  if (!res.ok()) {
    throw new Error(`accept failed (${res.status()}): ${await res.text()}`);
  }
}

export async function startEscrow(request, posterToken, taskId) {
  const res = await request.post(`${API_BASE}/api/tasks/${taskId}/escrow/start`, {
    headers: authHeaders(posterToken),
  });
  if (!res.ok()) {
    throw new Error(`escrow start failed (${res.status()}): ${await res.text()}`);
  }
  return res.json();
}

export async function uploadEvidenceUrls(request, taskerToken, taskId) {
  const res = await request.post(`${API_BASE}/api/tasks/${taskId}/evidence`, {
    headers: authHeaders(taskerToken),
    data: {
      before_image_url: "https://example.com/e2e-before.jpg",
      after_image_url: "https://example.com/e2e-after.jpg",
    },
  });
  if (!res.ok()) {
    throw new Error(`evidence failed (${res.status()}): ${await res.text()}`);
  }
}

export async function verifyTask(request, posterToken, taskId) {
  const res = await request.post(`${API_BASE}/api/tasks/${taskId}/verify`, {
    headers: authHeaders(posterToken),
  });
  if (!res.ok()) {
    throw new Error(`verify failed (${res.status()}): ${await res.text()}`);
  }
  return res.json();
}

export async function releaseEscrow(request, posterToken, taskId) {
  const res = await request.post(`${API_BASE}/api/tasks/${taskId}/escrow/release`, {
    headers: authHeaders(posterToken),
  });
  if (!res.ok()) {
    throw new Error(`release failed (${res.status()}): ${await res.text()}`);
  }
  return res.json();
}

export async function openDispute(request, token, taskId, reason) {
  const res = await request.post(`${API_BASE}/api/tasks/${taskId}/disputes`, {
    headers: authHeaders(token),
    data: { reason },
  });
  if (!res.ok()) {
    throw new Error(`dispute open failed (${res.status()}): ${await res.text()}`);
  }
  return res.json();
}

export async function resolveDispute(request, adminToken, disputeId, outcome, note) {
  const res = await request.post(`${API_BASE}/api/tasks/disputes/${disputeId}/resolve`, {
    headers: authHeaders(adminToken),
    data: { outcome, note },
  });
  if (!res.ok()) {
    throw new Error(`dispute resolve failed (${res.status()}): ${await res.text()}`);
  }
  return res.json();
}

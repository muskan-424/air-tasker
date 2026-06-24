import { defineConfig, devices } from "@playwright/test";
import { e2eBackendEnv } from "./e2e/global-setup.mjs";

const API_PORT = process.env.PLAYWRIGHT_API_PORT || "4000";
const WEB_PORT = process.env.PLAYWRIGHT_WEB_PORT || "3000";
const API_BASE = `http://localhost:${API_PORT}`;
const WEB_BASE = `http://localhost:${WEB_PORT}`;

const backendEnv = e2eBackendEnv();

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.mjs",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: WEB_BASE,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  globalSetup: "./e2e/global-setup.mjs",
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : [
        {
          command: `python -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
          cwd: "../backend_fastapi",
          url: `${API_BASE}/api/health`,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
          env: backendEnv,
        },
        {
          command: process.env.CI
            ? `npm run start -- --port ${WEB_PORT}`
            : `npm run dev -- --port ${WEB_PORT}`,
          url: WEB_BASE,
          reuseExistingServer: !process.env.CI,
          timeout: process.env.CI ? 180_000 : 300_000,
          env: {
            NEXT_PUBLIC_API_REWRITE_TARGET: API_BASE,
          },
        },
      ],
});

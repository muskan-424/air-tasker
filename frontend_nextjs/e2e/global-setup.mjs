import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendDir = path.join(path.dirname(fileURLToPath(import.meta.url)), "../../backend_fastapi");

function loadDotEnv(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    out[trimmed.slice(0, idx)] = trimmed.slice(idx + 1);
  }
  return out;
}

export function e2eBackendEnv() {
  const fileEnv = loadDotEnv(path.join(backendDir, ".env"));
  return {
    ...fileEnv,
    ...process.env,
    DATABASE_URL:
      process.env.DATABASE_URL ||
      fileEnv.DATABASE_URL ||
      "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/airtasker",
    SECRET_KEY:
      process.env.SECRET_KEY ||
      fileEnv.SECRET_KEY ||
      "e2e-test-secret-do-not-use-in-production",
    NOTIFICATION_RETRY_INTERVAL_SECONDS: "0",
    RAG_REINDEX_INTERVAL_HOURS: "0",
    USE_PINECONE_RAG: "false",
    RAZORPAY_WEBHOOK_EVENTS_CLEANUP_INTERVAL_HOURS: "0",
    USE_MOCK_CHATBOT: "true",
    GEMINI_API_KEY: "",
  };
}

export default async function globalSetup() {
  if (process.env.PLAYWRIGHT_SKIP_MIGRATE === "1") return;

  try {
    execSync("python -m alembic upgrade head", {
      cwd: backendDir,
      stdio: "inherit",
      env: e2eBackendEnv(),
    });
  } catch (err) {
    if (process.env.PLAYWRIGHT_SKIP_MIGRATE === "1") return;
    throw err;
  }
}

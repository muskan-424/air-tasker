# Agentic Chatbot Implementation Checklist

This checklist follows the proposal and implementation plan, and is organized for phased delivery.

## Phase A - Core Agentic Chatbot (FastAPI backend)

- [x] Add authenticated chatbot API routes.
- [x] Add basic intent routing for app-help, order lookup, task discovery, and task creation guidance.
- [x] Add simple RAG retrieval over local project docs.
- [x] Add "corrective/refine" response endpoint.
- [x] Keep architecture Gemini-ready and Pinecone-ready with config toggles.
- [x] Add persistent chat sessions and message history tables.
- [x] Add multilingual prompt templates and tone controls (`tone` on `AgentChatRequest`: friendly / professional / concise; language hint in Gemini prompts; `DEFAULT_CHAT_TONE` in config).

## Phase B - Tool-Enabled Transactional Agent

- [x] "Mera last 5 order dikhao" via structured tool call (`order_lookup` + numeric limit).
- [x] "Near high earning tech tasks" recommendation tool with filters (published tasks; `tech` keyword filter).
- [x] "Create task from chat" action to draft structured task JSON and publish confirmation flow (`build_ai_schema_from_message` → `TaskDraft`; `publish` / `go live` / latest draft → `publish_draft_to_task`).
- [x] "Apply through chatbot" action with acknowledgement flow (`apply_to_task` + DB).
- [x] Add confidence scores and safe fallback responses (`confidence` / `needs_verification` on `AgentChatResponse`; RAG uses chunk scores; tools use heuristics; low confidence skips Gemini when `SKIP_GEMINI_ON_LOW_CONFIDENCE` and appends note when `LOW_CONFIDENCE_APPEND_NOTE`).

## Phase C - Real RAG with Pinecone

- [x] Create embeddings pipeline and chunking strategy (Gemini `text-embedding-004` + mock fallback; shared chunking with local RAG).
- [x] Upsert docs/policies/help content into Pinecone namespace(s) (`doc_index_service`, `scripts/index_docs_to_pinecone.py`, `POST /api/admin/rag/reindex`).
- [x] Query Pinecone for top-k relevant context (`PineconeVectorStore` + `HybridRAGService` with local fallback).
- [x] Add source grounding metadata in responses (chunk `source`, Pinecone score in agent trace / stitched lines).
- [x] Add periodic re-index job for updated docs (`RAG_REINDEX_INTERVAL_HOURS` + background task on app lifespan when `USE_PINECONE_RAG`).

## Phase D - Gemini Integration

- [x] Replace rule-based final response with Gemini orchestration (tools/RAG produce FACTS; Gemini rewrites when `GEMINI_API_KEY` set and `USE_MOCK_CHATBOT=false`).
- [x] Add tool-calling with structured outputs (`POST /api/chat/classify` + `gemini_structured_service.classify_message` JSON intent/entities; Gemini JSON mode when API enabled, else rule fallback).
- [x] Add prompt guardrails for security, policy, and hallucination reduction (system + FACTS-only constraints in `gemini_chat_service`).
- [x] Add latency-aware model routing (fast vs quality) (`GEMINI_MODEL_FAST`, `GEMINI_MODEL_QUALITY`, `GEMINI_QUALITY_MIN_TOTAL_CHARS`; synthesis + refine pick model from prompt size / intent).

## Phase E - Voice Chat

- [x] Voice input endpoint (speech -> text) (`POST /api/voice/transcribe` — stub; wire Whisper/Google STT).
- [x] Optional text-to-speech output (`POST /api/voice/tts` — stub metadata).
- [x] Language detection and translation bridge (`POST /api/chat/translate`: Gemini when `GEMINI_API_KEY` + `USE_MOCK_CHATBOT=false`; `source_lang=auto` returns `detected_source_lang`; else stub).
- [x] Conversation mode for low-latency interaction (`WebSocket` `GET /api/chat/ws?token=<JWT>`; JSON messages with `type: message|ping`; full `AgentChatResponse` in reply — not token streaming).

## Phase F - Security and Verification

- [x] OTP for email/phone verification at onboarding (`POST /api/verification/email/request-otp`, `/email/verify`; SMTP optional, stub logs).
- [x] OTP challenge for sensitive profile changes (same `OtpPurpose.SENSITIVE_ACTION` flow).
- [x] Session/device verification for risky actions (`POST /api/verification/devices/register` fingerprint storage).
- [x] Audit logging (`audit_logs` table + `write_audit`; task publish writes audit).

## Phase G - Notifications

- [x] Real-time in-app notifications for task/escrow/dispute events (`notifications` table; `GET /api/notifications`; publish creates in-app notif; `GET /api/notifications/ws?token=<JWT>` pushes live events; optional `REDIS_URL` pub/sub fanout across API workers via channel `airtasker:notifications`).
- [x] Email notification channel for critical events (via `send_email` stub/SMTP + prefs gates).
- [x] Notification preferences in user settings (`GET/PUT /api/notifications/preferences`).
- [x] Delivery status tracking and retries (`delivery_status` + automated worker retries via `notifications.retry_failed` queue job).

## Phase H - Performance, Reliability, and Scale

- [x] Add Redis caching for frequent chatbot queries (`cache_get`/`cache_set` when `REDIS_URL` set; in-memory fallback).
- [x] Add queue workers for heavy AI jobs (in-process `job_queue` + worker lifespan; `POST /api/admin/jobs/enqueue`).
- [x] Add observability dashboards (latency, errors, fallback rate) (`GET /api/metrics/internal/summary` admin + `http_requests_total` counter; not Grafana — JSON).
- [x] Add notification observability + controls (`GET /api/metrics/internal/notifications`; `POST /api/admin/jobs/notifications/retry-failed`; `POST /api/admin/jobs/notifications/retry-failed/sync` for immediate retry).
- [x] Add rate limiting and abuse protection (SlowAPI on auth + verification).
- [x] Add load/performance test scripts (`scripts/smoke_load.py` concurrent GET /).
- [x] Add pytest smoke tests (`tests/test_health.py`) and optional DB integration tests (`tests/integration/`, set `RUN_INTEGRATION_TESTS=1`) for auth, task lifecycle, disputes, admin notification ops, and live notification WebSocket delivery.

## Phase I - Payments (India / Razorpay MVP)

- [x] Razorpay Order API for escrow funding (`POST /api/payments/razorpay/order` with `task_id`; stores `razorpay_order_id` on `escrow_payments`; returns `key_id` for Checkout).
- [x] Razorpay webhooks (`POST /api/webhooks/razorpay`) with `X-Razorpay-Signature` verification when `RAZORPAY_WEBHOOK_SECRET` is set; `payment.captured` records `razorpay_payment_id` + `PAYMENT_CAPTURED` escrow event.
- [x] Enforce webhook signing outside development/test (returns 503 when secret is missing in non-dev env); add policy tests.
- [x] Webhook replay dedupe: store Razorpay top-level `id` in `razorpay_webhook_events` (unique); duplicate deliveries short-circuit before business logic.
- [x] Scheduled cleanup of old `razorpay_webhook_events` rows (`RAZORPAY_WEBHOOK_EVENTS_RETENTION_DAYS` + `RAZORPAY_WEBHOOK_EVENTS_CLEANUP_INTERVAL_HOURS`; set interval `0` to disable).
- [x] Payments observability + ops controls (`GET /api/metrics/internal/payments`; `POST /api/admin/jobs/payments/razorpay-webhooks/purge` with audit log).
- [x] Alembic migration for `razorpay_payment_id` + enum `PAYMENT_CAPTURED`.
- [x] Dispute cancel path + admin manual path issue Razorpay refunds; store `razorpay_refund_id` + `REFUND_ISSUED` escrow event; metrics `razorpay_refunds_total`.
- [x] Razorpay `refund.processed` webhook: match escrow by `razorpay_payment_id`, idempotent refund id reconciliation, dedupe via existing `razorpay_webhook_events`.
- [x] Razorpay `refund.failed` webhook: log + metric `razorpay_webhook_refund_failed_total` (no DB reads; works with or without top-level event `id`).

## Phase J - Payments follow-ups (optional / incremental)

- [x] Tasker payout (RazorpayX): `users.razorpay_contact_id` / `razorpay_fund_account_id`; `POST /api/payments/razorpay/payout/register-bank` (tasker); `POST /api/payments/razorpay/payout/initiate-escrow` (admin/reviewer retry); auto payout after escrow `RELEASED` (`payout_status` on release response); `escrow_payments.razorpay_payout_id` + `PAYOUT_INITIATED` event; config `RAZORPAY_PAYOUT_ACCOUNT_NUMBER`.

## Phase K - Payout lifecycle (RazorpayX webhooks)

- [x] `escrow_payments.razorpay_payout_status` (Razorpay payout `status`); set on create-payout API response + webhook updates.
- [x] Webhook handling via `sync_payout_escrow_from_webhook`: `payout.processed` / `payout.failed` / `payout.reversed` → escrow events `PAYOUT_PROCESSED` / `PAYOUT_FAILED` / `PAYOUT_REVERSED`; other `payout.*` (except downtime) → `PAYOUT_UPDATED`; metrics `razorpay_webhook_payout_*_total`.
- [x] Payments snapshot: `escrow_payout_status_processed`, `escrow_payout_status_failed`.

## Phase L - KYC (India, provider-ready)

- [x] `user_kyc_profiles` (one per user): `status` pending / verified / rejected; store `full_name`, `pan_last4`, optional `aadhaar_last4` only (never full PAN).
- [x] `GET /api/kyc/me`, `POST /api/kyc/submit` (rate-limited); stub provider + `KYC_STUB_AUTO_VERIFY` for instant verify vs admin queue.
- [x] `GET /api/kyc/admin/pending`, `POST /api/kyc/admin/{user_id}/review` (admin/reviewer); audit actions `kyc_submit`, `kyc_admin_review`.
- [x] Config: `KYC_PROVIDER`, `KYC_STUB_AUTO_VERIFY`.

## Phase M - KYC integrations (pluggable + ops)

- [x] Provider abstraction (`KycProvider`, `StubKycProvider`, `get_kyc_provider()`); submission flows through `submit_kyc()`.
- [x] `POST /api/webhooks/kyc` async vendor callback (`provider_reference_id` + `status` verified/rejected/failed); optional `X-KYC-Signature` HMAC-SHA256(hex); 503 without secret outside dev/test.
- [x] `GET /api/metrics/internal/kyc` (admin) — counts by KYC status.

## Phase N - KYC ↔ payouts (trust)

- [x] Optional gate `KYC_REQUIRED_FOR_PAYOUT`: `POST /api/payments/razorpay/payout/register-bank` returns 403 if tasker KYC not `verified`; automatic `try_escrow_payout_to_tasker` returns `skipped_kyc_not_verified` when enabled.

## Phase O - Docker (local API + Postgres)

- [x] `backend_fastapi/Dockerfile` (Python 3.12-slim): install deps, copy app + Alembic; `docker-entrypoint.sh` runs `alembic upgrade head` (retry) then `uvicorn`.
- [x] `backend_fastapi/.dockerignore` to keep image small.
- [x] Repo root `docker-compose.yml`: `db` (Postgres 16, healthcheck), `api` (port 4000, `DATABASE_URL` to `db`); optional `redis` with profile `cache`.

## Phase P - Docker DX + env hygiene

- [x] Add `backend_fastapi/.env.docker.example` for compose defaults (`DATABASE_URL` points to `db` service).
- [x] Use compose `env_file` to keep app env centralized instead of hardcoded inline values.
- [x] Add `README.md` Docker quickstart and optional Redis profile run command.

## Phase Q - Docker production overlay

- [x] Add `docker-compose.prod.yml` override for production defaults (`ENVIRONMENT=production`, no dev `env_file`, restart policy).
- [x] Require runtime `DATABASE_URL` and `SECRET_KEY` via Compose variable guards.
- [x] Keep Postgres port unpublished in production override by default.
- [x] Document production compose command and required env vars in `README.md`.

## Phase R - Docker healthchecks and startup diagnostics

- [x] Add API container healthcheck in compose using /api/health.
- [x] Add production overlay API healthcheck for operational readiness checks.
- [x] Document post-start verification commands (docker compose ps, docker compose logs api).
## Phase S - Docker production security tightening

- [x] Run API container as non-root user in `backend_fastapi/Dockerfile`.
- [x] Add prod API `cap_drop: [ALL]` and `security_opt: [no-new-privileges:true]`.
- [x] Document production hardening posture in `README.md`.

## Phase T - Docker operational polish

- [x] Add `docker-compose.staging.yml` for staging-specific runtime defaults.
- [x] Add basic production resource guardrails (`mem_limit`, `cpus`) in `docker-compose.prod.yml`.
- [x] Extend `README.md` with staging command and concise ops runbook (restart/logs/rebuild/stop).

## Phase U - Backup, restore, and migration recovery runbook

- [x] Add Postgres backup and restore commands for docker-compose flows.
- [x] Add migration recovery steps (`alembic current/history/upgrade/stamp`) for incident handling.
- [x] Add concise emergency checklist for safe recovery and validation.

## Phase V - Monitoring and alerting runbook

- [x] Add monitoring runbook section covering API health, DB status, and worker/retry signals.
- [x] Add starter alert thresholds for uptime, error rate, restart churn, and retry-failure spikes.
- [x] Add first-response and escalation checklist for incident handling.

## Phase W - Deploy smoke-test and readiness runbook

- [x] Add pre-deploy checklist for env/secrets, backup confirmation, and migration awareness.
- [x] Add post-deploy readiness checks (`ps`, health, logs, alembic current).
- [x] Add minimum critical smoke tests and explicit rollback trigger criteria/actions.

## Phase X - Security and compliance runbook

- [x] Add secrets rotation checklist and post-rotation verification guidance.
- [x] Add least-privilege/access-control operational checks.
- [x] Add audit/evidence checklist and immediate containment steps for incidents.

## Phase Y - SLO/SLA and on-call handoff runbook

- [x] Define starter SLO targets for availability, latency, and critical job reliability.
- [x] Add severity matrix and response-time expectations for incidents.
- [x] Add on-call handoff template and shift-close checklist.

## Phase Z - Final release checklist and go-live signoff

- [x] Add go-live readiness checklist (env, migrations, health, smoke tests, backup).
- [x] Add change-freeze/communication items and ownership expectations.
- [x] Add reusable go-live signoff template and first-60-minute monitoring checks.

## Acceptance Criteria

- Chatbot answers app/help questions accurately.
- Chatbot can fetch user task history and recommend relevant jobs.
- Chatbot guides task creation naturally in human tone.
- System remains stable under concurrent load with safe fallbacks.


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

- [x] Real-time in-app notifications for task/escrow/dispute events (`notifications` table; `GET /api/notifications`; publish creates in-app notif).
- [x] Email notification channel for critical events (via `send_email` stub/SMTP + prefs gates).
- [x] Notification preferences in user settings (`GET/PUT /api/notifications/preferences`).
- [x] Delivery status tracking and retries (`delivery_status` column; retries not automated — mark for worker).

## Phase H - Performance, Reliability, and Scale

- [x] Add Redis caching for frequent chatbot queries (`cache_get`/`cache_set` when `REDIS_URL` set; in-memory fallback).
- [x] Add queue workers for heavy AI jobs (in-process `job_queue` + worker lifespan; `POST /api/admin/jobs/enqueue`).
- [x] Add observability dashboards (latency, errors, fallback rate) (`GET /api/metrics/internal/summary` admin + `http_requests_total` counter; not Grafana — JSON).
- [x] Add rate limiting and abuse protection (SlowAPI on auth + verification).
- [x] Add load/performance test scripts (`scripts/smoke_load.py` concurrent GET /).

## Acceptance Criteria

- Chatbot answers app/help questions accurately.
- Chatbot can fetch user task history and recommend relevant jobs.
- Chatbot guides task creation naturally in human tone.
- System remains stable under concurrent load with safe fallbacks.

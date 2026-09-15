# Local Project Progress Summary

This file is for local reference only.
Last updated: 2026-09-15

## Overall Status

- Core agentic chatbot phases are completed end-to-end.
- Payments + Razorpay escrow/payout + webhook lifecycle work is implemented.
- KYC (provider-ready) flows and webhook handling are implemented.
- Docker local/staging/prod setup and operations runbooks are documented.
- Trust & safety (disputes, reports, heuristics), ratings/reviews, and a dual-role
  offers marketplace are implemented.
- Task discovery is implemented: PIN/category/remote filters, free-text search,
  budget range filter, and a List/Map view (Leaflet + an offline India PIN
  geocoder) on the tasker feed.
- Public Q&A on tasks, phone (OTP) verification, and legal pages (terms, privacy,
  cancellation policy, community guidelines) are implemented.
- Beta onboarding checklist and branded email OTP delivery are implemented.
- Test coverage and policy checks were added for key critical flows; CI is green
  on `main` through PR #26.

## What Has Been Completed So Far

### 1) Agentic Chatbot Platform (Phases A-H)

- Authenticated chatbot API and intent routing.
- Local RAG + Pinecone-ready retrieval and reindex flows.
- Gemini orchestration with guardrails and routing.
- Gemini voice STT and vision-based before/after task verification, with
  stub/rule-based fallbacks when Gemini is disabled.
- OTP/security verification and audit logging.
- Notifications (in-app, websocket, retry workflows).
- Reliability and observability foundations (queue workers, metrics, rate limits, smoke tests).

### 2) India Payments + Escrow (Phases I-K)

- Razorpay order creation for escrow funding.
- Verified webhook processing and replay dedupe.
- Refund lifecycle handling (`refund.processed`, `refund.failed`) with reconciliation support.
- Tasker payout foundations (RazorpayX contact/fund account/payout initiation).
- Payout lifecycle status tracking with webhook-driven escrow events.
- Internal metrics and admin ops endpoints for payments.

### 3) KYC + Trust Controls (Phases L-N, plus later trust/dispute work)

- `user_kyc_profiles` model and migration.
- User submission and admin review endpoints.
- Pluggable KYC provider abstraction (stub provider included).
- KYC webhook endpoint with signature policy enforcement.
- KYC internal metrics endpoint.
- Optional payout gating when KYC is not verified.
- Disputes UI, admin reviewer dashboard, user reports, and trust heuristics/flags.
- Ratings and reviews (Phase S).

### 4) Marketplace, Discovery & Onboarding (later feature work)

- Task hub (`/tasks/[id]`) with status timeline, poster-tasker chat with
  translation, and scope/price propose-and-accept feeding escrow.
- Offers marketplace, dual-role poster/tasker accounts, task cancellation, and
  service fees.
- Public task Q&A, phone (OTP) verification, and legal pages.
- Beta onboarding checklist and improved email OTP delivery.
- Task discovery: text search, budget filters, and a List/Map toggle backed by
  an offline India PIN → lat/lng lookup; category taxonomy expanded from 5 to
  10 categories (added gardening, painting, tech, moving, tutoring, events).

### 5) Docker + Ops Readiness (Phases O-Z)

- Dockerized FastAPI backend and compose stack with Postgres (+ optional Redis).
- Entrypoint migration handling and startup behavior.
- Staging + production compose overlays.
- Healthchecks, container hardening, and resource guardrails.
- Operational runbooks in README:
  - backup/restore
  - migration recovery
  - incident monitoring/alerting
  - deployment smoke tests + rollback criteria
  - security/compliance operations
  - SLO/SLA + on-call handoff
  - final go-live signoff template

## Recent Milestone PRs (merged to `main`)

- PR #26 — Task discovery: search, budget filters, and map view
- PR #25 — Task discovery, public Q&A, phone verification, and legal pages
- PR #24 — Offers, dual-role accounts, task cancellation, and service fees
- PR #23 — Beta onboarding checklist and OTP improvements
- PR #22 — Gemini voice STT and vision verification
- PR #21 — Task hub, per-task chat, and scope agreement
- PR #20 — Product UI polish for beta

## Remaining Local Notes

- `ai_airtasker_india_proposal.md` and `implementation_plan_india.md` are
  committed (tracked since `3fbbd7e`); the earlier note that they were
  local-only was stale and has been corrected here.
- [launch/GO_LIVE_SIGNOFF.md](launch/GO_LIVE_SIGNOFF.md) has open pre-flight
  items: secrets rotation, a fresh DB backup/restore test, a staging rollback
  drill, live Grafana dashboards, and a smoke-test re-run (the last recorded
  run predates PRs #20-#26).

## Suggested Next Practical Steps

- Re-run `python scripts/smoke_deploy.py` against a current staging deploy —
  the last recorded pass predates the last seven merged PRs.
- Work through the remaining [GO_LIVE_SIGNOFF.md](launch/GO_LIVE_SIGNOFF.md)
  pre-flight checklist items ahead of a first production launch.
- Manually verify the discovery search/map feature (PR #26) end-to-end in a
  running instance: keyword search, budget range, List/Map toggle, and marker
  placement for the beta PIN cluster (248001, 110001, 560001).

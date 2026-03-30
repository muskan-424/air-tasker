# AI-First Airtasker Clone for India: Implementation Plan + Tech Stack

This document describes an end-to-end, step-by-step implementation plan for building an AI-native services marketplace for India, inspired by Airtasker-style workflows.

## 1. Project Scope (What we are building)

### Users
- **Poster**: creates tasks using **voice** and/or **image**, confirms AI draft, and pays via escrow.
- **Tasker**: builds skill profile, accepts tasks, communicates with translation, performs work, uploads evidence.
- **Admin/Reviewer (MVP fallback)**: resolves low-confidence verification and disputes.

### Core promises
- Reduce friction: AI converts messy requests into a **structured task**.
- Remove language barriers: AI translation in chat.
- Increase trust: escrow + vision-based evidence verification with confidence thresholds.
- Keep it India-ready: PIN-based location, Razorpay + UPI escrow, consent-first Aadhaar/PAN KYC workflow.

## 2. Definitions (MVP terms)

- **Task schema**: strict JSON output produced by the AI Task Generator and stored as the single source of truth for matching, UI, evidence requirements, and verification.
- **Escrow**: funds are held via Razorpay until completion verification passes.
- **Confidence gate**: if vision confidence is high, escrow releases automatically; otherwise, dispute/manual review triggers.
- **Dispute**: a user-initiated (or auto-triggered) process when evidence verification fails or conflicts occur.

## 3. Success Metrics (MVP)

- AI parsing accuracy: % of AI outputs that match the task JSON schema and contain required fields.
- Time saved: median time from raw request to published task.
- Match quality: accept rate and task start rate.
- Completion rate: % of tasks that reach completion evidence upload.
- Dispute rate: % of tasks that end in dispute/manual review.
- Verification quality: precision/recall for pass/fail decisions and frequency of “low-confidence fallback.”
- Dispute resolution time: average resolution duration (target 24-48 hours for MVP).

## 4. Tech Stack (Recommended)

This is a practical stack that keeps the AI layer modular and the marketplace workflow reliable.

### Frontend (Web first, Mobile later)
- **Next.js (React)**: fast web UI for Posters/Taskers + admin queue.
- **React Native + Expo**: wrap the app for iOS/Android after the web MVP is stable.
- **Audio capture**: use a React Native audio recording module (mobile) and file upload (web).

### Backend (API + real-time)
- **Node.js + Express** (or **Python + FastAPI** if you prefer Python for ML integration).
- **WebSockets** or **Socket.IO** for real-time chat and presence (optional for MVP; can start with polling).
- **Background jobs** (recommended): run AI calls, evidence verification, and webhook handling asynchronously.

### Database + Search
- **PostgreSQL**: relational data (users, tasks, chats metadata, payments, disputes).
- **Vector search**:
  - **pgvector** (recommended for simplicity) OR Pinecone if you prefer managed vectors.
  - Use embeddings for task text to match against tasker skills and category.

### AI Orchestration Layer
- **Speech-to-Text + Translation**: **Bhashini API** (India-focused) and/or Google APIs.
- **LLM for task generation & summarization**: Gemini 2.0 Flash (structured JSON output).
- **Vision verification**: Gemini Pro Vision (before/after comparison + confidence scoring).
- **Schema validation**: strict JSON validation (fail fast, retry generation, or ask clarifying questions).

### Payments & Identity
- **Razorpay**: escrow-like hold and payment event webhooks.
- **UPI split payments (if needed)**: handled via Razorpay features when finalizing payout logic.
- **Identity / KYC**: DigiLocker or Signzy (consent-first Aadhaar/PAN verification workflow).

### File Storage
- **Object storage** for evidence photos/videos (e.g., AWS S3 or equivalent).
- Store only necessary evidence references; keep access control strict.

### Deployment & Ops (baseline)
- **Docker** for local consistency.
- **CI/CD** pipeline to build/test/deploy (GitHub Actions or similar).
- **Monitoring**: logs + dashboards for AI latency/cost and payment state machines.

## 5. End-to-End Implementation Flow (From Start to End)

### A. Poster flow (full lifecycle)
1. Poster opens the app and selects:
   - category
   - location (PIN code + optional landmark)
2. Poster creates a task using:
   - **voice note** (AI STT + translation + task schema output), and/or
   - **image upload** (vision identifies issue + task schema output)
3. System returns a **task draft** that follows the strict task JSON schema.
4. Poster reviews/edits the draft:
   - confirms required tools
   - confirms completion criteria
   - confirms evidence requirements
5. Poster publishes the task.
6. Taskers see the task in their personalized feed and accept it by acknowledging requirements.
7. Poster and tasker negotiate within guardrails (AI-mediated if enabled):
   - AI suggests a fair range
   - final agreement is stored as scope evidence for dispute prevention
8. Poster triggers payment:
   - payment is authorized/held in escrow via Razorpay.
9. During task execution, chat runs with AI translation.
10. After completion, tasker uploads evidence:
   - before/after photos (and optional video)
11. Vision verification runs:
   - returns confidence score + pass/low-confidence/fail decision
12. Outcome:
   - **high confidence**: escrow releases automatically
   - **low confidence**: dispute/manual review lane opens
13. Poster rates/records outcome and dispute results (if any).

### B. Tasker flow (full lifecycle)
1. Tasker onboarding:
   - completes skills + experience + service areas (PIN regions)
2. Tasker receives personalized tasks (AI matching).
3. Tasker reviews task requirements and accepts only if aligned.
4. Tasker communicates in local language via translation chat.
5. Tasker completes work and uploads evidence.
6. System verifies with vision confidence:
   - pass -> escrow release
   - low confidence -> dispute/manual review
7. Tasker sees result and rating.

### C. Admin/Reviewer flow (failure handling)
1. Trigger: low confidence verification or dispute submission.
2. Admin queue shows:
   - task schema
   - chat summary
   - evidence thumbnails and extracted verification notes
3. Admin decision:
   - approve pass -> release escrow
   - fail -> hold/partial refund rules
4. Decision is recorded in audit logs and the workflow updates automatically.

## 6. Data Model (Minimum entities for MVP)

Implement these tables/collections early to support reliable workflow state transitions.

Core:
- `users` (poster/tasker/admin roles)
- `user_profiles` (skills, language preferences, PIN service areas)
- `task_drafts` (AI output before publish)
- `tasks` (published task with stored schema JSON)
- `task_acceptances` (tasker acceptance + timestamp)
- `scopes` (final agreed scope and price snapshot)
- `chat_sessions` and `chat_messages` (store original + translated)
- `evidence_uploads` (links to stored media)
- `verification_results` (confidence score, status, explanation)
- `escrow_payments` and `escrow_events` (state machine)
- `disputes` and `dispute_events` (state + decisions)
- `admin_review_queue` (manual review items)

## 7. Step-by-Step Implementation Plan (Phases)

### Phase 0: Setup (Before building features)
1. Create the project workspace structure (frontend, backend, shared types).
2. Add environment configuration:
   - AI API keys
   - Razorpay keys
   - storage credentials
3. Configure CI checks:
   - linting
   - formatting
   - unit tests (basic)

Definition of Done:
- You can run frontend + backend locally with config loaded safely.

### Phase 1: Authentication + Task Draft (Week 1-2)
1. Implement auth:
   - role-based access (poster vs tasker)
2. Implement task draft APIs:
   - create task draft from user input (mock AI output at first)
3. Implement poster UI:
   - voice/image upload endpoints (wire to backend)
   - draft preview and edit
4. Implement publish endpoint:
   - persist task schema JSON into `tasks`

Definition of Done:
- Poster can publish a task using a draft.

### Phase 2: AI Task Generator MVP (Week 2-3)
1. Integrate STT + translation:
   - voice note -> transcript -> task draft input
2. Integrate Vision-to-task:
   - image -> task draft output
3. Enforce strict task schema validation:
   - if invalid JSON -> retry with constrained prompt or ask clarifying questions
4. Add “AI explanation” field (short, user-friendly):
   - what fields were inferred and why (kept minimal for MVP)

Definition of Done:
- AI can generate a valid task schema for MVP categories.

### Phase 3: Matching + Accept Flow (Week 3-5)
1. Build tasker skill profile intake.
2. Create embeddings pipeline:
   - task description embeddings
   - tasker skills embeddings
3. Matching v1:
   - vector similarity + PIN filtering + category filter
4. Task acceptance:
   - tasker accepts only after acknowledging evidence requirements

Definition of Done:
- Published tasks appear in tasker feed and can be accepted.

### Phase 4: Escrow + Dispute Hooks (Week 4-6)
1. Razorpay integration:
   - create order/payment intent
   - handle webhooks (authorized/paid)
2. Escrow state machine:
   - held -> releaseEligible -> released OR disputeOpened
3. Dispute trigger:
   - user opens dispute manually
   - auto opens dispute on low-confidence verification
4. Minimal dispute UI:
   - upload additional evidence notes/photos

Definition of Done:
- Payment workflow is correct and auditable.

### Phase 5: Evidence Upload + Vision Verification (Week 5-7)
1. Evidence upload UI:
   - before/after photos (required by schema)
2. Evidence processing pipeline:
   - save file -> call vision model -> store verification result
3. Confidence thresholds + fallback:
   - high confidence -> release
   - low confidence -> manual review lane
4. Admin review UI (basic):
   - evidence thumbnails + schema + explanation + chat summary

Definition of Done:
- Completing a task can release escrow or open review.

### Phase 6: Translation Chat MVP (Week 6-8)
1. Implement translated chat:
   - detect language preferences
   - store original + translated message
2. Add chat summary for disputes:
   - short summary generated from message history (optional for MVP, can do later)

Definition of Done:
- Posters and taskers can chat in their languages.

### Phase 7: Trust & Safety + KYC Workflow (Week 8-10)
1. KYC onboarding plan:
   - consent-first verification via partner workflow
2. Gatekeeping (MVP approach):
   - verified users can accept higher-value tasks (configurable)
3. Reporting + appeals:
   - basic report forms
   - disputes and KYC appeals routed to admin review
4. Fraud heuristics (starter rules):
   - suspicious cancellation patterns
   - repeated evidence mismatch signals

Definition of Done:
- Safety workflows exist and are recorded end-to-end.

### Phase 8: Closed Beta + Iteration (Week 10+)
1. Launch in a limited neighborhood/region:
   - start with 3-8 categories only
2. Enable only AI features that are stable:
   - keep fallback/manual path always available
3. Monitor KPIs:
   - AI cost per task
   - dispute rate
   - verification pass rate
4. Iterate prompts, thresholds, and evidence requirements:
   - reduce low-confidence fallbacks over time

Definition of Done:
- Stable closed beta with measurable KPIs.

## 8. Testing Plan (Must-Do)

### Unit tests
- task schema validation logic
- pricing guardrails logic
- state machine transitions for escrow/disputes

### Integration tests
- AI generation returns valid schema (with fixtures)
- vision verification saves verification results correctly
- razorpay webhook handling updates escrow state correctly

### End-to-end tests (happy path + dispute path)
- happy path: publish -> accept -> pay/hold -> evidence -> release
- dispute path: publish -> accept -> evidence low confidence -> manual review -> resolution

## 9. Notes for India Readiness (What to emphasize)

To keep it India-ready, highlight in your implementation details:
- PIN-based location and service area filtering
- Razorpay + UPI escrow flow
- consent-first Aadhaar/PAN via DigiLocker/Signzy partner
- multilingual translation (start with English + a couple of target languages)
- dispute/manual review fallback for AI verification uncertainty

## 10. Next Questions (Optional, to tailor your MVP)

- Which 3 categories will you launch first?
- Which 2-3 languages for the beta?
- Which backend preference: Node/Express or FastAPI?


# VayuTask AI — Help & FAQ

## What does this app do?

VayuTask AI is an India-focused gig marketplace (similar to Airtasker). Posters describe tasks in plain language; AI structures them into a task contract. Taskers discover nearby jobs, apply, complete work, upload before/after evidence, and get paid through escrow after verification.

## How do I post a task?

1. Sign in as a **Poster**.
2. Use **AI Task Generator** (`/poster`) or the **agent chat** (`/chat`) — describe the job in Hindi, English, or Hinglish.
3. Review the AI-generated draft (category, budget, location PIN, evidence rules).
4. **Publish** to make the task visible on the tasker feed.

## How does escrow work?

Escrow holds the poster's payment safely until the job is verified:

1. Poster funds escrow (Razorpay order) after a tasker is assigned.
2. Tasker completes the job and uploads **before/after photos** (and optional video).
3. Poster or system runs **verification** on the evidence.
4. On **PASS**, escrow becomes eligible for **release** to the tasker.
5. Disputes pause automatic release until resolved.

Escrow protects both sides: posters pay only after evidence; taskers know funds are reserved.

## How does verification work?

After completion, evidence is checked (AI vision or rule-based MVP):

- **PASS** — strong before/after proof; escrow can move toward release.
- **LOW_CONFIDENCE** — partial proof; manual review recommended.
- **FAIL** — insufficient proof; poster may dispute or request more evidence.

Verification results are stored on the task record for audit.

## What if a task is disputed?

Either party can open a **dispute** with a reason. While disputed:

- Escrow release is blocked.
- Admin or automated rules may request more evidence.
- Resolution outcomes: release to tasker, refund poster, or partial settlement (per policy).

Dispute events are logged for transparency.

## Chatbot agent vs task chat

- **Agent chat** (`/chat`) — AI assistant for orders, help, creating tasks, finding jobs.
- **Task chat** (future) — direct poster ↔ tasker messaging on a specific job.

## Payments (India)

Razorpay handles order creation and webhook capture for escrow funding. KYC may be required before tasker payouts in production.

## Privacy & safety

- Do not share OTPs or passwords in chat.
- Use in-app verification and escrow rather than off-platform payments when possible.
- Report suspicious behaviour via dispute flow.

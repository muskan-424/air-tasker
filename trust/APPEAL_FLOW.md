# Trust & safety — appeal flow (beta)

Manual appeals during closed beta. Automated enforcement is limited to **trust flags** for admin review.

## When a user is flagged

Trust heuristics may raise flags for:

| Rule | Meaning |
|------|---------|
| `repeated_cancellations` | Many task acceptances cancelled in a short window |
| `evidence_mismatch_pattern` | Multiple failed or low-confidence verifications |
| `new_account_velocity` | New account posting many tasks in 24 hours |

Flags appear in **Admin → Trust flags**. They do **not** auto-ban accounts in beta.

## User report flow

1. User submits **Report** from `/disputes` (task ID + category + reason) or `POST /api/reports`.
2. Report enters **Admin → Reports** queue (`OPEN`).
3. Reviewer marks **reviewed** or **dismissed** with optional notes.

## Appeal (manual, beta)

1. User emails support (see `beta/SUPPORT_PLAYBOOK.md`) with:
   - Account email
   - Report or flag ID (if known)
   - Short explanation + any evidence
2. Reviewer checks audit log + task history.
3. Outcomes:
   - **Uphold** — keep flag; may restrict payouts or require extra KYC (manual ops).
   - **Clear** — resolve trust flag; dismiss report if applicable.
4. Document decision in report `admin_notes` via admin dashboard or API.

## API (ops)

- `GET /api/reports/open` — open reports (ADMIN/REVIEWER)
- `POST /api/reports/{id}/resolve` — `{ "outcome": "reviewed"|"dismissed", "admin_notes": "..." }`
- `GET /api/reports/trust-flags/active` — active heuristic flags

## Production note

Before go-live, define SLA (e.g. 48h appeal response) and link this doc from the in-app help FAQ.

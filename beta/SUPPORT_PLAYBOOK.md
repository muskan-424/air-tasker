# Closed beta support playbook (Phase Y)

Audience: beta operators, moderators, and on-call during the limited launch.

## Scope

| Dimension | Closed beta value |
|-----------|-------------------|
| **Categories** | electrical, plumbing, cleaning |
| **PIN cluster** | 248001 (Dehradun), 110001 (Delhi NCR), 560001 (Bengaluru) |
| **Languages** | English, Hindi, Tamil |

## Triage flow

1. **User reports issue** → ask for task ID, PIN, category, and screenshot.
2. **Check KPIs** → `GET /api/beta/kpis` (admin JWT) for accept rate, dispute rate, time-to-publish.
3. **Classify severity**
   - **Sev-1:** payments/escrow broken, auth down, data loss risk → escalate immediately.
   - **Sev-2:** task publish/accept blocked for many users → fix config or deploy within 4h.
   - **Sev-3:** UI polish, single-user edge case → log feedback, batch for next release.

## Common fixes

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Task not on radar | PIN outside beta cluster | Poster must include allowed PIN in draft; tasker sets service PIN in profile |
| Publish rejected | Category not in beta list | Use electrical/plumbing/cleaning wording in draft |
| KYC/payout blocked | `KYC_REQUIRED_FOR_PAYOUT=true` | Complete KYC on `/kyc` or admin approves stub submission |
| Razorpay checkout missing | Feature flag off or keys unset | Enable `FEATURE_FLAG_RAZORPAY_CHECKOUT` + Razorpay env vars |
| AI chat unavailable | Feature flag off or Gemini key missing | Enable `FEATURE_FLAG_AI_CHAT` + `GEMINI_API_KEY` |

## Feature flags (backend env)

| Variable | Default | Module |
|----------|---------|--------|
| `BETA_MODE_ENABLED` | true | Category/PIN enforcement on publish |
| `FEATURE_FLAG_AI_CHAT` | true | `/chat` nav + agent |
| `FEATURE_FLAG_VOICE_INPUT` | true | Voice on poster page |
| `FEATURE_FLAG_KYC_PAYOUT` | true | `/kyc` nav |
| `FEATURE_FLAG_RAZORPAY_CHECKOUT` | true | `/payments` Razorpay step |
| `FEATURE_FLAG_DISPUTES` | true | Dispute API paths |

## Feedback collection

- Users: `/feedback` in the web app → `POST /api/beta/feedback`
- Review: query `beta_feedback` table or export for weekly beta review

## KPI targets (starter)

Track weekly during beta:

- **Time to publish** (median draft → publish): under 5 minutes
- **Accept rate**: > 40% of published tasks accepted within 48h
- **Dispute rate**: < 5% of escrow tasks
- **AI cost per task**: monitor `ai_cost_inr_estimated` from `/api/beta/kpis`

## Escalation contacts

Fill before launch:

- **Beta lead:** _name / email_
- **Engineering on-call:** _name / phone_
- **Payments (Razorpay):** _merchant support ticket process_

## Go / no-go for expanding beta

Expand PINs or categories only when:

- 10+ tasks completed end-to-end in staging/production beta
- No open Sev-1 incidents for 7 days
- Accept rate and dispute rate within targets above

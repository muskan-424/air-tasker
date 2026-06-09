# Change freeze and stakeholder communications (Phase Z)

Use **7 days before** production go-live and again **24 hours before** the window.

## Change freeze scope

| In scope (frozen) | Out of scope (allowed) |
|-------------------|-------------------------|
| `main` branch merges except hotfix | Security patches with release owner approval |
| Production env var changes | Monitoring dashboard tweaks |
| Database schema changes without migration review | Beta feedback triage (no code deploy) |

**Freeze start (UTC):** _______________  
**Freeze end (UTC):** _______________ (after 24h stable prod)

## Internal announcement (Slack / email)

**Subject:** VayuTask AI production go-live — change freeze `[DATE]`

Team,

We are targeting production go-live on **[DATE/TIME UTC]**.

- **Release owner:** [NAME]
- **Rollback owner:** [NAME]
- **On-call:** [NAME]
- **Change freeze:** [START] → [END]
- **Staging smoke:** passed on [DATE]
- **User impact:** brief API restarts during deploy (~5 min)

During the window please avoid merges to `main` unless approved by the release owner.

Dashboards: Grafana ops overview · `/api/health` · `/metrics`

Rollback owner executes [ROLLBACK_DRILL.md](./ROLLBACK_DRILL.md) if smoke or 60-minute watch fails.

## Beta user communication (optional)

**Subject:** VayuTask closed beta — scheduled maintenance

We will perform a platform upgrade on **[DATE]**. The app may be unavailable for up to 5 minutes. PIN clusters and categories unchanged: electrical, plumbing, cleaning in Dehradun / Delhi NCR / Bengaluru.

Feedback: in-app `/feedback` or support email.

## Post-deploy all-clear

**Subject:** VayuTask go-live complete — monitoring active

Deploy completed at **[TIME UTC]**. Smoke tests passed. 60-minute watch running. Report issues to on-call with task ID and screenshot.

## Escalation

| Severity | Contact |
|----------|---------|
| Sev-1 (payments/auth down) | Rollback owner + release owner immediately |
| Sev-2 (degraded core path) | On-call engineer within 30 minutes |
| Sev-3 (UI/minor) | Next business day |

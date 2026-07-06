# Go-live signoff (Phase Z)

Complete this document for every production release. Store signed copy in your release tracker (Notion/Jira/Drive).

## Release metadata

| Field | Value |
|-------|-------|
| **Release version / git tag** | `6c5a03f` |
| **Git commit** | `6c5a03f39b58ae766bc1ae7d741c3433c4fcfaee` |
| **Alembic head** | `m5n6o7p8q9r0` |
| **Environment** | staging (local validated 2026-07-02) |
| **Release owner** | _fill before prod_ |
| **Rollback owner** | _fill before prod_ |
| **On-call engineer** | _fill before prod_ |
| **Change window (UTC)** | _fill before prod_ |
| **Linked PRs / changelog** | PR #17 trust/reports, PR #18 ratings (Phase S), PR #19 go-live/beta tooling |

## Pre-flight checklist

- [x] All PRs merged to `main`; CI green (backend, integration, frontend, E2E, smoke-staging)
- [ ] `.env.production.example` reviewed; secrets set in host (not in git)
- [ ] `SECRET_KEY`, Razorpay, webhook secrets rotated if this is first prod launch
- [ ] DB backup taken and restore tested within last 7 days
- [x] `alembic upgrade head` planned; downgrade path documented if migration is risky
- [x] Local/staging passed `python scripts/smoke_deploy.py` against `http://localhost:4000` (2026-07-02)
- [ ] Staging rollback drill completed once (see [ROLLBACK_DRILL.md](./ROLLBACK_DRILL.md))
- [ ] Grafana dashboards live ([observability/README.md](../observability/README.md))
- [x] Beta scope confirmed with product ([beta/SUPPORT_PLAYBOOK.md](../beta/SUPPORT_PLAYBOOK.md))

## Deploy execution

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose exec api alembic current
python scripts/smoke_deploy.py https://YOUR_PROD_API
```

| Check | Result | Notes |
|-------|--------|-------|
| `docker compose ps` all healthy | ☐ pass ☐ fail | |
| `GET /api/health` | ☐ pass ☐ fail | |
| Smoke script | ☐ pass ☐ fail | |
| Frontend login + one task path | ☐ pass ☐ fail | |

## Rollback decision

| Option | Selected |
|--------|----------|
| Rollback **not needed** | ☐ |
| Rollback **triggered** (see ROLLBACK_DRILL.md) | ☐ |

**Rollback trigger criteria (any one):** API unhealthy > 5 min; 5xx > 5% for 5 min; migration mismatch; payment webhooks failing.

## Open risks accepted for this release

_List known non-blockers (e.g. voice beta disabled, single-region deploy)._

1.
2.

## Signoff

| Role | Name | Date (UTC) | Signature / approval |
|------|------|------------|----------------------|
| Release owner | | | |
| Engineering lead | | | |
| Product / beta lead | | | |

## Post go-live (first 60 minutes)

Run:

```bash
python scripts/go_live_watch.py --base-url https://YOUR_PROD_API --minutes 60 --interval 60
```

- [ ] No sustained 5xx spike on Grafana
- [ ] Razorpay test webhook received (if configured)
- [ ] One real beta task completed or dry-run verified
- [ ] No Sev-1/Sev-2 alerts open at T+60m

**24h review (DoD):** Production healthy 24h; no unresolved Sev-1; rollback path proven on staging.

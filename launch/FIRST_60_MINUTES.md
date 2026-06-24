# First 60 minutes monitoring (Phase Z)

Run immediately after production deploy and smoke pass.

## Automated watch

```bash
python scripts/go_live_watch.py --base-url https://YOUR_PROD_API --minutes 60 --interval 60
```

Or from repo root:

```bash
npm run go-live:watch -- --base-url https://YOUR_PROD_API
```

The script samples every 60s (configurable):

| Signal | Source |
|--------|--------|
| API health | `GET /api/health` |
| Webhook readiness | `GET /api/health/webhooks` |
| 5xx counter | `GET /metrics` → `vayutask_http_responses_5xx_total` |

**Auto-rollback hint:** exits non-zero if health fails 3 samples in a row.

## Manual checklist (T+0 → T+60)

| Time | Action | ☐ |
|------|--------|---|
| T+0 | Confirm smoke + signoff doc started | |
| T+5 | Grafana: request rate, p95 latency, 5xx | |
| T+10 | Check Razorpay webhook dashboard (if live) | |
| T+15 | Verify one auth register/login on prod frontend | |
| T+30 | Review API logs: `docker compose logs api --tail 200` | |
| T+45 | Check notification retry metrics (admin JSON or Grafana) | |
| T+60 | Close watch script; update signoff doc | |

## Grafana panels to watch

From [observability/grafana/dashboards/vayutask-ops-overview.json](../observability/grafana/dashboards/vayutask-ops-overview.json):

- HTTP 5xx rate — alert if > 5% of traffic for 5 minutes (README threshold)
- p95 latency — target under 800ms on core routes
- Razorpay webhook counters — should increment on test payment
- Notification retry failures — should not climb continuously

## Admin JSON endpoints (JWT admin)

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://YOUR_PROD_API/api/metrics/internal/payments
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://YOUR_PROD_API/api/beta/kpis
```

## When to rollback

See [ROLLBACK_DRILL.md](./ROLLBACK_DRILL.md) — do not wait past T+15 if payments or auth are broken.

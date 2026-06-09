# Observability (Phase V)

Prometheus metrics from the FastAPI API plus Grafana dashboards for local/staging ops.

## Metrics endpoint

- **Prometheus scrape:** `GET /metrics` (also `GET /api/metrics/prometheus`)
- **Admin JSON (legacy):** `GET /api/metrics/internal/*` (requires admin JWT)

Set `ENABLE_PROMETHEUS_METRICS=false` to disable the scrape endpoint.

Exported series include:

| Metric | Purpose |
|--------|---------|
| `vayutask_http_requests_total{method,status}` | Request volume |
| `vayutask_http_request_duration_seconds` | Latency histogram |
| `vayutask_http_responses_5xx_total` | Server errors |
| `vayutask_job_queue_depth` | In-process job queue |
| `vayutask_*` business counters | Razorpay, notifications, KYC (mirrors internal JSON counters) |

## Start Grafana + Prometheus

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

| Service | URL |
|---------|-----|
| Grafana | http://localhost:3001 (admin / admin) |
| Prometheus | http://localhost:9090 |
| API metrics | http://localhost:4000/metrics |

Dashboard **VayuTask AI — Ops Overview** loads automatically under folder **VayuTask AI**.

## Alert thresholds (from README runbook)

Use these as Grafana alert rule starting points:

- 5xx rate > 5% of total requests for 5 minutes
- `vayutask_job_queue_depth` > 0 for 10 minutes (stuck worker)
- Notification retry failures increasing for 10 minutes
- API target down for > 2 minutes (`up{job="vayutask-api"} == 0`)

Admin JSON endpoints remain useful for deep dives during incidents (`/api/metrics/internal/payments`, etc.).

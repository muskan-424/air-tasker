# Staging deployment (Phase X)

Always-on staging for demos and QA: API + Postgres via Docker Compose, with automated post-deploy smoke checks.

## Quick start (local staging)

```bash
cp .env.staging.example .env.staging
# edit SECRET_KEY and CORS_ALLOWED_ORIGINS

docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build -d
python scripts/smoke_deploy.py http://localhost:4000
```

Frontend (separate host, e.g. Vercel preview):

```bash
cd frontend_nextjs
cp .env.local.example .env.local
# NEXT_PUBLIC_API_REWRITE_TARGET=https://your-staging-api.example.com
# NEXT_PUBLIC_WS_BASE=wss://your-staging-api.example.com
npm run build && npm run start
```

## Smoke script

`scripts/smoke_deploy.py` runs the README deploy smoke checklist:

| Check | Endpoint |
|-------|----------|
| Health | `GET /api/health` |
| Capabilities | `GET /api/health/capabilities` |
| Webhook readiness | `GET /api/health/webhooks` |
| Auth | register + login |
| Task flow | draft → publish |
| Metrics | `GET /metrics` (if enabled) |
| Payments policy | poster denied on payout status |

```bash
SMOKE_BASE_URL=https://staging-api.example.com python scripts/smoke_deploy.py
```

From repo root: `npm run smoke:staging`

## CORS

Set `CORS_ALLOWED_ORIGINS` to your staging frontend URL(s), comma-separated. Do not use `*` in shared staging/production.

## HTTPS reverse proxy (example)

See `staging/nginx.conf.example` for TLS termination in front of the API container. Terminate TLS at nginx and proxy to `api:4000`.

## Cloud deploy notes

| Platform | Approach |
|----------|----------|
| **VPS** | Docker Compose staging overlay + nginx + certbot |
| **Railway / Render** | Deploy `backend_fastapi` Dockerfile; attach managed Postgres; set env from `.env.staging.example` |
| **Frontend** | Vercel/Netlify preview → set `CORS_ALLOWED_ORIGINS` to preview URL |

After deploy, run smoke against the public URL:

```bash
python scripts/smoke_deploy.py https://staging-api.yourdomain.com
```

## Closed beta (Phase Y)

See [beta/SUPPORT_PLAYBOOK.md](../beta/SUPPORT_PLAYBOOK.md) for category/PIN limits, feature flags, and KPI targets.
Admin KPIs: `GET /api/beta/kpis` (admin JWT).

## Observability

Optional Grafana stack (Phase V):

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.observability.yml --profile observability up -d
```

Grafana: http://localhost:3001

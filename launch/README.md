# Production go-live (Phase Z)

Controlled production launch using repo runbooks, signoff templates, and automated checks.

| Document | Purpose |
|----------|---------|
| [GO_LIVE_SIGNOFF.md](./GO_LIVE_SIGNOFF.md) | Fillable signoff for each release |
| [CHANGE_FREEZE_COMMS.md](./CHANGE_FREEZE_COMMS.md) | Stakeholder + change freeze templates |
| [FIRST_60_MINUTES.md](./FIRST_60_MINUTES.md) | Post-deploy monitoring checklist |
| [ROLLBACK_DRILL.md](./ROLLBACK_DRILL.md) | Staging rollback exercise |
| [../deploy/ORACLE_VERCEL.md](../deploy/ORACLE_VERCEL.md) | **$0 deploy:** Vercel + Oracle + Cloudflare Tunnel |

## Quick commands

```bash
# 1. Deploy production overlay
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# 2. Smoke
python scripts/smoke_deploy.py https://api.yourdomain.com

# 3. Watch first hour
python scripts/go_live_watch.py --base-url https://api.yourdomain.com

# 4. Rollback drill (staging, before prod)
python scripts/rollback_drill.py --base-url http://localhost:4000

# 5. Beta cohort readiness (staging URL required)
npm run beta:check -- --base-url http://localhost:4000

# 6. Signoff metadata (paste into GO_LIVE_SIGNOFF.md)
npm run release:metadata
```

Env template: [.env.production.example](../.env.production.example)

## Release order reminder

Merge and validate on staging before production:

1. CI pipeline → 2. E2E → 3. Disputes/admin → 4. Observability → 5. Staging smoke → 6. Closed beta → 7. **Go-live signoff (this folder)**

# Rollback drill (Phase Z)

**Goal:** Prove you can return to last known good release on staging before production go-live.

**DoD:** Drill executed once on staging; post-rollback smoke passes; steps recorded in [GO_LIVE_SIGNOFF.md](./GO_LIVE_SIGNOFF.md).

## Prerequisites

- Staging stack running (`docker-compose.staging.yml`)
- Known good git tag recorded (e.g. last staging deploy)
- `python scripts/smoke_deploy.py` passes against staging URL

## Automated helper

```bash
# Baseline smoke + print rollback commands
python scripts/rollback_drill.py --base-url http://localhost:4000 --previous-tag v0.9.0-staging

# After you manually roll back, verify smoke again
python scripts/rollback_drill.py --base-url http://localhost:4000 --verify-after
```

From repo root: `npm run rollback:drill`

## Manual drill steps

1. **Record baseline**
   ```bash
   git rev-parse HEAD
   docker compose exec api alembic current
   python scripts/smoke_deploy.py http://localhost:4000
   ```

2. **Simulate bad deploy** (staging only)
   - Deploy a deliberately broken config _or_ note current HEAD as "bad" without actually breaking prod.
   - Optional: set invalid `SECRET_KEY` in staging env and restart API to verify smoke fails.

3. **Execute rollback**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.staging.yml down
   git checkout <LAST_GOOD_TAG>
   docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build -d
   docker compose exec api alembic current
   ```

4. **Verify recovery**
   ```bash
   python scripts/smoke_deploy.py http://localhost:4000
   python scripts/go_live_watch.py --minutes 5 --interval 30
   ```

5. **Document**
   - Time to detect, time to rollback, issues found
   - Update signoff template "Rollback drill completed on staging: [DATE]"

## Production rollback (real incident)

Same steps using `docker-compose.prod.yml` and production secrets snapshot. Notify stakeholders using [CHANGE_FREEZE_COMMS.md](./CHANGE_FREEZE_COMMS.md) post-deploy all-clear template (failure variant).

**Never** force-push `main` or run destructive DB commands without backup.

## Rollback trigger criteria

- API unhealthy > 5 minutes post deploy
- 5xx rate > 5% for 5 minutes
- Alembic revision mismatch / crash loop
- Payment webhooks failing with user impact

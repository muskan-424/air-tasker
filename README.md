# AI-First Airtasker Clone for India 🚀

An AI-native peer-to-peer services marketplace optimized for the Indian gig economy. This platform uses AI to reduce friction, eliminate language barriers, and ensure fair pricing.

## 🌟 Core Features

- **AI Task Parsing (For Posters):**
  - **Voice-to-Task:** Record audio in native languages to auto-generate structured tasks.
  - **Image-to-Task:** Upload photos for Vision AI to analyze and suggest job descriptions.
  - **Smart Budgeting:** AI suggests a fair price range based on historical data.

- **AI Matchmaking & Vetting (For Taskers):**
  - **Skill Extraction:** AI extracts skills from voice chats or past work photos.
  - **Hyper-Personalized Feed:** Precise task pushing based on location, performance, and skills.

- **AI-Mediated Communication:**
  - **Real-time Translation Chat:** Seamless cross-language communication.
  - **Auto-Negotiator Bot:** Mediates fair pricing automatically.

- **Trust & Safety:**
  - **Automated KYC:** Facial recognition matching with Aadhaar/PAN.
  - **Outcome Verification:** Vision AI verifies "before" and "after" photos before escrow release.

## 💻 Tech Stack
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL (with Alembic for migrations)
- **AI Models:** Gemini 2.0 Flash & Pro Vision, Bhashini API
- **Payments & Identity:** Razorpay (Escrow), DigiLocker API

## 🛠 Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/muskan-424/air-tasker.git
   cd air-tasker
   ```
2. **Setup Backend:**
   Navigate into the `backend_fastapi` directory, configure your `.env` based on `.env.example`, and install the dependencies from `requirements.txt`.

## Docker Quickstart (Backend + Postgres)

From repo root:

```bash
docker compose up --build
```

- API: `http://localhost:4000`
- Health: `GET /api/health`
- Postgres: `localhost:5432` (`postgres` / `postgres`, db `airtasker`)

Optional Redis profile:

```bash
docker compose --profile cache up --build
```

Notes:
- Compose uses `backend_fastapi/.env.docker.example` for API env vars.
- For real deployments, copy to your own env file and set strong secrets/real keys (`SECRET_KEY`, Razorpay, KYC webhook secret, etc.).

### Staging overlay

Use staging overrides for pre-production testing:

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build -d
```

### Production overlay

Use the production override file to avoid local defaults:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

After startup, verify container health with `docker compose ps` and `docker compose logs api --tail 100`.

Production hardening in this overlay:
- API runs as a non-root user from the image.
- Linux capabilities dropped (`cap_drop: [ALL]`) and `no-new-privileges` enabled.
- Basic resource guardrails (`mem_limit`, `cpus`) are set for API and DB.

Minimum required shell env vars before running the command:
- `DATABASE_URL`
- `SECRET_KEY`

Example (PowerShell):

```powershell
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@db:5432/airtasker"
$env:SECRET_KEY="replace-with-long-random-secret"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```


### Ops runbook (quick)

- Restart API: `docker compose restart api`
- Follow API logs: `docker compose logs -f api`
- Recreate API only after image updates: `docker compose up -d --no-deps --build api`
- Stop stack: `docker compose down`
- Rollback (previous image tag flow): update image tag/env and rerun `docker compose up -d`


### Backup and restore (Postgres)

Create a backup from the running `db` service:

```bash
docker compose exec -T db pg_dump -U postgres -d airtasker > backup_$(date +%Y%m%d_%H%M%S).sql
```

Restore from a backup file:

```bash
docker compose exec -T db psql -U postgres -d airtasker < backup_20260331_120000.sql
```

For production/staging, keep backups outside the host machine and rotate old dumps.

### Migration recovery runbook

- Check migration state: `docker compose exec api alembic current`
- List available migrations: `docker compose exec api alembic history --verbose`
- Apply pending migrations: `docker compose exec api alembic upgrade head`
- If startup fails repeatedly, inspect: `docker compose logs api --tail 200`
- Emergency only (after DB backup): align revision with `docker compose exec api alembic stamp <revision>` and rerun `alembic upgrade head`

### Emergency checklist

- Pause write traffic to API (or scale API to zero before DB surgery).
- Take a fresh DB backup before any manual migration action.
- Verify `/api/health` and key payment/KYC routes after recovery.
- Record incident notes: failing migration ID, root cause, and corrective action.


### Monitoring and alerting runbook

What to watch:
- API health endpoint: `GET /api/health` should stay healthy.
- API errors: sustained 5xx spikes in app logs.
- DB health: Postgres container status and restart count.
- Queue/worker behavior: stuck retries or repeated failed jobs in logs.

Suggested alert thresholds (starting point):
- API unavailable for > 2 minutes.
- 5xx error rate > 5 percent for 5 minutes.
- DB container restart > 3 times in 10 minutes.
- Notification/payment retry failures increasing continuously for 10 minutes.

First response checklist:
- Confirm service state: `docker compose ps`.
- Check API logs: `docker compose logs api --tail 200`.
- Check DB logs: `docker compose logs db --tail 200`.
- Verify health endpoint and one critical flow (auth + task/payment/KYC path).
- If config or secret issue, fix env and redeploy only API: `docker compose up -d --no-deps --build api`.

Escalation guidance:
- If data integrity is in doubt, pause writes and take backup immediately.
- If webhook/payment events are affected, record impacted window and reconcile via admin metrics/endpoints after recovery.
- Capture incident timeline, root cause, and preventive actions before closing.


### Deploy smoke-test and readiness runbook

Pre-deploy checklist:
- Confirm required env vars are present (`DATABASE_URL`, `SECRET_KEY`, payment/KYC secrets as applicable).
- Ensure DB backup exists for the current deploy window.
- Confirm migration plan (new Alembic revision reviewed; rollback approach noted).

Deploy command (prod overlay):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Post-deploy readiness checks:
- Service status: `docker compose ps`
- API health: `curl http://localhost:4000/api/health`
- API logs: `docker compose logs api --tail 200`
- DB logs: `docker compose logs db --tail 200`
- Migration state: `docker compose exec api alembic current`

Critical smoke tests (minimum):
- Auth path: login/register endpoint responds successfully.
- Core task path: list/create task path works.
- Payments/KYC path: one representative protected endpoint returns expected auth/policy behavior.

Rollback trigger criteria:
- API stays unhealthy for > 5 minutes post deploy.
- 5xx error rate remains elevated after one restart attempt.
- DB migration mismatch or repeated startup crash loops.

Rollback action:
- Revert image/env to last known good release and run `docker compose up -d`.
- Re-check health, logs, and one critical smoke path before closing incident.


### Security and compliance runbook

Secrets rotation checklist:
- Rotate `SECRET_KEY`, payment keys, and webhook secrets on a fixed schedule.
- Update secrets in deployment environment first, then restart only affected services.
- Verify auth token issuance/validation and webhook signature checks after rotation.

Access control and least privilege:
- Restrict production compose access to trusted operators only.
- Use separate credentials for staging and production; do not reuse admin secrets.
- Review admin/reviewer roles regularly and remove stale privileged accounts.

Audit and traceability checks:
- Confirm audit logs are written for sensitive admin actions.
- Keep deployment/change records with operator name, time, and reason.
- Preserve API/DB logs for incident windows and regulatory review periods.

Security incident evidence checklist:
- Incident start/end time and impacted components.
- Affected user/task/payment identifiers (redact personal data in shared notes).
- Relevant logs, alert snapshots, and mitigation steps taken.
- Recovery verification evidence (`/api/health`, key flow checks) and follow-up actions.

Immediate containment steps:
- Revoke/rotate suspected leaked credentials.
- Block suspicious traffic sources (WAF/reverse-proxy/firewall level).
- Temporarily disable risky endpoints/features if active abuse is ongoing.
- Escalate to incident owner and document every containment action.


### SLO/SLA and on-call handoff runbook

Service objectives (starter targets):
- API availability SLO: 99.5 percent monthly (`/api/health` uptime).
- P95 API latency SLO: under 800 ms for core authenticated routes.
- Critical job reliability SLO: >= 99 percent successful completion/retry recovery.

Incident severity matrix:
- Sev-1: Full outage, data integrity risk, or payment flow unavailable.
- Sev-2: Partial outage, elevated 5xx/latency, degraded critical path.
- Sev-3: Non-critical degradation or intermittent issues with workaround.

Response targets (SLA-style internal):
- Sev-1: acknowledge within 10 minutes, mitigation in progress within 20 minutes.
- Sev-2: acknowledge within 30 minutes, mitigation in progress within 60 minutes.
- Sev-3: acknowledge within 4 hours, fix scheduled in next planned cycle.

On-call handoff template:
- Current incident/state summary.
- Impacted services/routes and user impact.
- Actions taken so far and current hypothesis.
- Dashboards/log links and exact time window.
- Next 2-3 prioritized actions and explicit owner.

Shift-close checklist:
- Confirm alerts are stable for at least one monitoring window.
- Ensure tickets/incidents include root cause and follow-up tasks.
- Record any temporary mitigations that still need permanent fixes.


### Final release checklist and go-live signoff

Go-live readiness checklist:
- All required env vars/secrets set for target environment.
- Latest migrations applied and verified (`alembic current` at expected head).
- Health checks green and no sustained 5xx spikes.
- Critical smoke tests pass (auth, tasks, payments/KYC policy paths).
- Backup for current release window exists and restore path is validated.

Change freeze and communication:
- Define release window and temporary change freeze scope.
- Share rollout plan, owner, and rollback owner in advance.
- Notify support/stakeholders about expected impact window.

Go-live signoff template:
- Release version/tag:
- Environment:
- Release owner:
- Start time / End time:
- Migration status:
- Smoke test result summary:
- Open risks (if any):
- Rollback decision (Not needed / Triggered):
- Final signoff by:

Post go-live (first 60 minutes):
- Watch error rate, latency, restart count, and queue failures.
- Validate one real user-critical flow end-to-end.
- Confirm no abnormal alerts remain open.

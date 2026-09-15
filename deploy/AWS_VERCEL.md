# Deploy VayuTask AI — Vercel + AWS EC2 + Cloudflare

**Frontend:** Vercel (free)
**API + Postgres:** AWS EC2 (free-tier eligible `t3.micro`/`t4g.micro`, or size up for real prod load)
**HTTPS/WSS:** Cloudflare Tunnel (free — required because Vercel is HTTPS)

This mirrors [ORACLE_VERCEL.md](./ORACLE_VERCEL.md) but targets an EC2 instance and uses the
hardened `docker-compose.prod.yml` overlay (resource limits, dropped capabilities,
`ENVIRONMENT=production`) instead of the beta-labeled staging overlay.

---

## Overview

```text
Browser → https://your-app.vercel.app          (Next.js)
       → https://your-tunnel.trycloudflare.com  (FastAPI + Postgres, on EC2)
```

---

## Phase 1 — EC2 instance (~30 min first time)

### 1.1 Launch the instance

1. AWS Console → **EC2 → Launch instance**
   - **AMI:** Ubuntu 22.04 or 24.04 LTS
   - **Instance type:** `t3.micro` or `t4g.micro` (free-tier eligible for 12 months on a new
     account; size up to `t3.small`/`t3.medium` once real beta traffic needs more headroom)
   - **Key pair:** create/download a new one — you'll need it to SSH in
   - **Storage:** 20-30 GB gp3 is plenty to start
2. **Security group:** allow inbound **TCP 22 (SSH)** from your IP only. The API is exposed
   through the Cloudflare Tunnel, so **do not** open port 4000 (or 5432) to the internet.
3. **Elastic IP (recommended):** allocate one and associate it with the instance so the
   public IP survives a stop/start — otherwise SSH/tunnel setup breaks on reboot.

### 1.2 SSH & bootstrap

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
curl -fsSL https://raw.githubusercontent.com/muskan-424/air-tasker/main/deploy/setup-aws-ec2.sh | bash
# Or clone repo and run: bash deploy/setup-aws-ec2.sh
```

Log out and back in after Docker install (group membership).

### 1.3 Configure secrets

```bash
cd air-tasker
nano .env.deploy
```

Generate `SECRET_KEY`:

```bash
openssl rand -hex 32
```

Set in `.env.deploy`:

- `SECRET_KEY` — from above
- `POSTGRES_PASSWORD` — strong password
- `DATABASE_URL` — same password in URL: `postgresql+asyncpg://postgres:YOUR_PASS@db:5432/airtasker`
- `CORS_ALLOWED_ORIGINS` — fill after Vercel (Phase 3), e.g. `https://air-tasker-xxx.vercel.app`
- Razorpay/Gemini/SMTP keys — see [.env.production.example](../.env.production.example) for
  the full list; rotate every secret rather than reusing staging values for the first real
  prod launch (see the [go-live checklist](../launch/GO_LIVE_SIGNOFF.md))

### 1.4 Start stack

Uses `docker-compose.prod.yml` (not the staging overlay) — resource limits, dropped
capabilities, and `ENVIRONMENT=production` are baked in.

```bash
set -a && source .env.deploy && set +a
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.deploy.yml up --build -d
curl http://localhost:4000/api/health
docker compose exec api alembic current
```

---

## Phase 2 — Cloudflare Tunnel (HTTPS for API)

On the EC2 instance (quick test — URL changes each run):

```bash
cloudflared tunnel --url http://localhost:4000
```

Copy the `https://....trycloudflare.com` URL.

**Stable tunnel (recommended for real prod):**

1. Free [Cloudflare dashboard](https://dash.cloudflare.com) account
2. **Zero Trust → Networks → Tunnels → Create**
3. Route public hostname (ideally your own domain) → `http://localhost:4000`
4. Run tunnel as a systemd service ([Cloudflare docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/))

Save your API URL: `https://YOUR-TUNNEL-HOST`

> Alternative for a "real" domain: put an Application Load Balancer + ACM certificate in
> front of the EC2 instance instead of Cloudflare Tunnel. That's more idiomatic AWS but adds
> setup cost/complexity that isn't justified yet at closed-beta scale — switch to it if/when
> you outgrow a single EC2 box.

### Smoke test (from your PC)

```bash
python scripts/smoke_deploy.py https://YOUR-TUNNEL-HOST
npm run beta:check -- --base-url https://YOUR-TUNNEL-HOST
```

---

## Phase 3 — Vercel frontend (~15 min)

1. [vercel.com](https://vercel.com) → Sign in with GitHub
2. **Add New Project** → import `muskan-424/air-tasker`
3. **Root Directory:** `frontend_nextjs`
4. **Environment variables** (Production):

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_BASE` | `https://YOUR-TUNNEL-HOST` |
| `NEXT_PUBLIC_WS_BASE` | `wss://YOUR-TUNNEL-HOST` |

5. **Deploy**

Copy Vercel URL: `https://your-app.vercel.app`

### Update CORS on EC2

```bash
nano .env.deploy
# CORS_ALLOWED_ORIGINS=https://your-app.vercel.app
set -a && source .env.deploy && set +a
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.deploy.yml up -d --build api
```

Redeploy Vercel if you changed env vars.

---

## Phase 4 — Verify

1. Open Vercel URL → Register → Login
2. Poster: publish a task in a beta category + PIN (e.g. *electrical wiring repair, PIN 248001*)
3. Tasker: accept on `/tasker`, try the new search/budget filters and map view
4. Chat: test WebSocket on `/chat`
5. Run `npm run beta:check -- --base-url https://YOUR-TUNNEL-HOST`

Work through [launch/GO_LIVE_SIGNOFF.md](../launch/GO_LIVE_SIGNOFF.md) in full before inviting
real users — this runbook only covers standing the stack up, not the backup/rollback/secrets
items in that checklist.

---

## Optional — Real email OTP

In `.env.deploy` on the EC2 instance:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-gmail-app-password
EMAIL_FROM=you@gmail.com
```

Restart API container after change.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Vercel UI loads, API 404/CORS | Check `NEXT_PUBLIC_API_BASE` and `CORS_ALLOWED_ORIGINS` |
| Chat broken | `NEXT_PUBLIC_WS_BASE` must be `wss://` same host as API |
| Publish 400 | Use beta category + PIN in task text |
| EC2 unreachable after reboot | Confirm an Elastic IP is associated (public IP otherwise changes) |
| SSH refused | Check security group still allows 22 from your current IP |
| Tunnel down | Restart the `cloudflared` service |

---

## Redeploy after code changes

**EC2:**

```bash
cd air-tasker && git pull
set -a && source .env.deploy && set +a
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.deploy.yml up --build -d
```

**Vercel:** auto-deploys on push to `main` if GitHub connected.

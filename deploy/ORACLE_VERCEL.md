# Deploy VayuTask AI ($0) — Vercel + Oracle + Cloudflare

**Frontend:** Vercel (free)  
**API + Postgres:** Oracle Cloud Always Free VM  
**HTTPS/WSS:** Cloudflare Tunnel (free — required because Vercel is HTTPS)

---

## Overview

```text
Browser → https://your-app.vercel.app          (Next.js)
       → https://your-tunnel.trycloudflare.com  (FastAPI + Postgres)
```

---

## Phase 1 — Oracle Cloud VM (~45 min first time)

### 1.1 Create account & VM

1. [cloud.oracle.com](https://cloud.oracle.com) → Sign up (Always Free).
2. **Compute → Instances → Create**
   - **Region:** India South (Hyderabad) or Mumbai if listed
   - **Image:** Ubuntu 22.04/24.04
   - **Shape:** Ampere `VM.Standard.A1.Flex` → **1 OCPU, 6 GB RAM** (free)
   - **Public IP:** assign
   - **SSH key:** download private key
3. **VCN security list:** allow inbound **TCP 22** (SSH only). API goes through Cloudflare Tunnel — do **not** need port 4000 public.

### 1.2 SSH & bootstrap

```bash
ssh -i your-key.pem ubuntu@YOUR_VM_PUBLIC_IP
curl -fsSL https://raw.githubusercontent.com/muskan-424/air-tasker/main/deploy/setup-oracle-vm.sh | bash
# Or clone repo and run: bash deploy/setup-oracle-vm.sh
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

### 1.4 Start stack

```bash
set -a && source .env.deploy && set +a
docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.deploy.yml up --build -d
curl http://localhost:4000/api/health
```

---

## Phase 2 — Cloudflare Tunnel (HTTPS for API)

On the VM (quick test — URL changes each run):

```bash
cloudflared tunnel --url http://localhost:4000
```

Copy the `https://....trycloudflare.com` URL.

**Stable tunnel (recommended):**

1. Free [Cloudflare dashboard](https://dash.cloudflare.com) account
2. **Zero Trust → Networks → Tunnels → Create**
3. Route public hostname → `http://localhost:4000`
4. Run tunnel as systemd service ([Cloudflare docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/))

Save your API URL: `https://YOUR-TUNNEL-HOST`

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

### Update CORS on VM

```bash
nano .env.deploy
# CORS_ALLOWED_ORIGINS=https://your-app.vercel.app
set -a && source .env.deploy && set +a
docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.deploy.yml up -d --build api
```

Redeploy Vercel if you changed env vars.

---

## Phase 4 — Verify

1. Open Vercel URL → Register → Login
2. Poster: publish task with *electrical wiring repair Dehradun PIN 248001*
3. Tasker: accept on `/tasker`
4. Chat: test WebSocket on `/chat`
5. Run `npm run beta:check -- --base-url https://YOUR-TUNNEL-HOST`

Fill [launch/GO_LIVE_SIGNOFF.md](../launch/GO_LIVE_SIGNOFF.md) and invite beta users.

---

## Optional — Real email OTP

In `.env.deploy` on VM:

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
| VM OOM | Use 6 GB ARM shape; don’t run Grafana on same VM |
| Tunnel down | Restart cloudflared service |

---

## Redeploy after code changes

**VM:**

```bash
cd air-tasker && git pull
set -a && source .env.deploy && set +a
docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.deploy.yml up --build -d
```

**Vercel:** auto-deploys on push to `main` if GitHub connected.

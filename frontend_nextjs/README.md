# VayuTask AI — Frontend (Next.js)

Web app for the India gig marketplace: poster sandbox, tasker radar, AI chat, vision verification, and Razorpay escrow flows.

## Prerequisites

- Node.js 20+
- FastAPI backend running at http://localhost:4000 (see repo root `README.md` — `docker compose up` or `npm run dev:backend`)

## Quick start

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_BASE` | *(empty)* | Full API URL prefix. Leave empty to use `/api` rewrites in dev. |
| `NEXT_PUBLIC_WS_BASE` | `ws://localhost:4000` | WebSocket origin for chat and notifications |
| `NEXT_PUBLIC_API_REWRITE_TARGET` | `http://localhost:4000` | Backend target for Next.js `/api/*` rewrites |

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing |
| `/login` | Register / login (Poster or Tasker) |
| `/poster` | Create task draft |
| `/tasker` | Task feed and accept |
| `/chat` | Agent WebSocket chat |
| `/verify` | Evidence upload and verification |
| `/payments` | Escrow + Razorpay order flow |

## Scripts

```bash
npm run dev      # development server (port 3000)
npm run build    # production build
npm run start    # serve production build
npm run lint     # ESLint
```

From repo root you can also run `npm run dev:frontend`.

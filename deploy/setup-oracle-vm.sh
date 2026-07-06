#!/usr/bin/env bash
# Bootstrap Ubuntu VM (Oracle Cloud Always Free). Run as ubuntu user after SSH login.
set -euo pipefail

echo "==> Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo "==> Installing cloudflared (Cloudflare Tunnel)..."
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) CF_ARCH=arm64 ;;
  x86_64|amd64) CF_ARCH=amd64 ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac
curl -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}" -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/cloudflared

echo "==> Clone repo (skip if already cloned)..."
if [ ! -d air-tasker ]; then
  git clone https://github.com/muskan-424/air-tasker.git
fi
cd air-tasker

echo "==> Create deploy env..."
if [ ! -f .env.deploy ]; then
  cp deploy/oracle.env.example .env.deploy
  echo "EDIT .env.deploy now: SECRET_KEY, POSTGRES_PASSWORD, DATABASE_URL, CORS_ALLOWED_ORIGINS"
  openssl rand -hex 32 | xargs -I{} sed -i "s/replace-with-openssl-rand-hex-32-output/{}/" .env.deploy 2>/dev/null || true
fi

echo ""
echo "Next steps:"
echo "  1. nano .env.deploy   # set passwords + CORS (Vercel URL)"
echo "  2. set -a && source .env.deploy && set +a"
echo "  3. docker compose -f docker-compose.yml -f docker-compose.staging.yml -f docker-compose.deploy.yml up --build -d"
echo "  4. curl http://localhost:4000/api/health"
echo "  5. cloudflared tunnel --url http://localhost:4000   # copy https URL for Vercel env"
echo "  See deploy/ORACLE_VERCEL.md for full guide."

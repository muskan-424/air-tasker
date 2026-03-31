#!/bin/sh
set -e
cd /app

echo "Applying database migrations..."
n=0
until alembic upgrade head; do
  n=$((n + 1))
  if [ "$n" -ge 60 ]; then
    echo "Alembic failed after 60 attempts; exiting." >&2
    exit 1
  fi
  echo "Alembic not ready — retrying ($n/60) in 2s..."
  sleep 2
done

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-4000}"

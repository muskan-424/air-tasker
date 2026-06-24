#!/usr/bin/env python3
"""First 60 minutes post go-live monitoring (Phase Z).

Polls health, webhook readiness, and Prometheus 5xx counters.

Usage:
  python scripts/go_live_watch.py
  python scripts/go_live_watch.py --base-url https://api.example.com --minutes 60 --interval 60
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime


def _get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return 0, str(exc)


def _parse_5xx_total(metrics_body: str) -> float | None:
    total = 0.0
    found = False
    for line in metrics_body.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("vayutask_http_responses_5xx_total"):
            found = True
            match = re.search(r"\}\s+(\d+(?:\.\d+)?)$", line) or re.search(r"\s(\d+(?:\.\d+)?)$", line)
            if match:
                total += float(match.group(1))
    return total if found else None


def run_watch(base_url: str, *, minutes: int, interval: int) -> int:
    base = base_url.rstrip("/")
    end_at = time.time() + minutes * 60
    consecutive_health_failures = 0
    sample = 0

    print(f"Go-live watch started at {datetime.now(UTC).isoformat()}Z")
    print(f"Target={base} duration={minutes}m interval={interval}s")

    while time.time() < end_at:
        sample += 1
        ts = datetime.now(UTC).strftime("%H:%M:%S")

        health_status, health_body = _get(f"{base}/api/health")
        health_ok = health_status == 200 and '"healthy"' in health_body

        hooks_status, hooks_body = _get(f"{base}/api/health/webhooks")
        hooks_ok = hooks_status == 200
        hooks_summary = ""
        if hooks_ok:
            try:
                hooks = json.loads(hooks_body)
                hooks_summary = (
                    f"razorpay_secret={'yes' if hooks.get('razorpay_webhook_secret_configured') else 'no'}"
                )
            except json.JSONDecodeError:
                hooks_summary = "webhooks_json_error"

        metrics_status, metrics_body = _get(f"{base}/metrics")
        five_xx = _parse_5xx_total(metrics_body) if metrics_status == 200 else None

        line = (
            f"[{ts}] sample={sample} health={'OK' if health_ok else 'FAIL'}({health_status}) "
            f"webhooks={'OK' if hooks_ok else 'FAIL'} {hooks_summary}"
        )
        if five_xx is not None:
            line += f" 5xx_total={five_xx}"
        else:
            line += " metrics=n/a"
        print(line)

        if health_ok:
            consecutive_health_failures = 0
        else:
            consecutive_health_failures += 1
            if consecutive_health_failures >= 3:
                print("ERROR: health failed 3 consecutive samples — consider rollback.", file=sys.stderr)
                return 1

        time.sleep(interval)

    print("Go-live watch completed without automatic rollback trigger.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor API for first 60 minutes after go-live")
    parser.add_argument("--base-url", default="http://localhost:4000", help="API base URL")
    parser.add_argument("--minutes", type=int, default=60, help="Watch duration in minutes")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between samples")
    args = parser.parse_args()
    return run_watch(args.base_url, minutes=args.minutes, interval=args.interval)


if __name__ == "__main__":
    raise SystemExit(main())

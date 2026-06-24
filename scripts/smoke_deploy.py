#!/usr/bin/env python3
"""Post-deploy smoke checks for staging/production (Phase X).

Usage:
  python scripts/smoke_deploy.py
  python scripts/smoke_deploy.py https://staging-api.example.com
  SMOKE_BASE_URL=http://localhost:4000 python scripts/smoke_deploy.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.error
import urllib.request


class SmokeError(Exception):
    pass


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    expected: tuple[int, ...] = (200,),
) -> dict | str:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
        if status not in expected:
            raise SmokeError(f"{method} {url} -> {status}: {raw[:400]}") from exc
        return json.loads(raw) if raw.startswith("{") or raw.startswith("[") else raw

    if status not in expected:
        raise SmokeError(f"{method} {url} -> {status}: {raw[:400]}")
    if not raw:
        return {}
    if raw.startswith("{") or raw.startswith("["):
        return json.loads(raw)
    return raw


def run_smoke(base_url: str) -> None:
    base = base_url.rstrip("/")
    print(f"Smoke testing {base}")

    health = _request("GET", f"{base}/api/health")
    if health.get("status") != "healthy":
        raise SmokeError(f"health status unexpected: {health!r}")
    print("  ok health")

    caps = _request("GET", f"{base}/api/health/capabilities")
    print(f"  ok capabilities env={caps.get('environment')}")

    hooks = _request("GET", f"{base}/api/health/webhooks")
    print(
        "  ok webhooks "
        f"razorpay_secret={'yes' if hooks.get('razorpay_webhook_secret_configured') else 'no'} "
        f"kyc_secret={'yes' if hooks.get('kyc_webhook_secret_configured') else 'no'}"
    )

    email = f"smoke_{uuid.uuid4().hex[:10]}@example.com"
    password = "SmokePass123!"
    reg = _request(
        "POST",
        f"{base}/api/auth/register",
        body={"email": email, "password": password, "role": "POSTER"},
    )
    token = reg["access_token"]
    print("  ok register")

    login = _request(
        "POST",
        f"{base}/api/auth/login",
        body={"email": email, "password": password},
    )
    if not login.get("access_token"):
        raise SmokeError("login missing access_token")
    print("  ok login")

    draft = _request(
        "POST",
        f"{base}/api/tasks/drafts",
        headers={"Authorization": f"Bearer {token}"},
        body={"raw_input": "Smoke test AC repair Dehradun PIN 248001", "language": "en"},
    )
    if not draft.get("id"):
        raise SmokeError("draft missing id")
    print(f"  ok task draft id={draft['id']}")

    publish = _request(
        "POST",
        f"{base}/api/tasks/{draft['id']}/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    if str(publish.get("status", "")).upper() != "PUBLISHED":
        raise SmokeError(f"publish unexpected: {publish!r}")
    print(f"  ok publish task_id={publish.get('id')}")

    metrics = _request("GET", f"{base}/metrics", expected=(200, 404))
    if metrics != {}:
        print("  ok prometheus /metrics")
    else:
        print("  skip prometheus /metrics (disabled)")

    # Protected payout endpoint should reject poster role.
    _request(
        "GET",
        f"{base}/api/payments/razorpay/payout/status",
        headers={"Authorization": f"Bearer {token}"},
        expected=(403,),
    )
    print("  ok payments auth policy (poster denied payout status)")

    print("Smoke checks passed.")


def main() -> int:
    base_url = (
        (sys.argv[1] if len(sys.argv) > 1 else None)
        or os.getenv("SMOKE_BASE_URL")
        or "http://localhost:4000"
    )
    try:
        run_smoke(base_url)
        return 0
    except SmokeError as exc:
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"SMOKE FAILED: cannot reach API: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

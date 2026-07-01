#!/usr/bin/env python3
"""Closed beta launch readiness check (Phase Y + Z).

Runs go-live preflight, smoke_deploy, and validates beta config on a live API.

Usage:
  python scripts/beta_launch_check.py --base-url http://localhost:4000
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_CATEGORIES = {"electrical", "plumbing", "cleaning"}
EXPECTED_PINS = {"248001", "110001", "560001"}


def _run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def _validate_beta_config(base_url: str) -> tuple[bool, str]:
    import json
    import urllib.request

    url = f"{base_url.rstrip('/')}/api/beta/config"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return False, f"cannot fetch beta config: {exc}"

    if not payload.get("beta_enabled"):
        return False, "beta_enabled is false — enable BETA_MODE_ENABLED for closed beta"

    categories = set(payload.get("categories") or [])
    missing_cats = EXPECTED_CATEGORIES - categories
    if missing_cats:
        return False, f"missing beta categories: {sorted(missing_cats)}"

    pins = set(payload.get("pin_codes") or [])
    missing_pins = EXPECTED_PINS - pins
    if missing_pins:
        return False, f"missing beta PIN codes: {sorted(missing_pins)}"

    flags = payload.get("feature_flags") or {}
    disabled = [name for name, enabled in flags.items() if not enabled]
    if disabled:
        print(f"  warn feature flags off: {', '.join(disabled)}")

    return True, f"beta scope ok ({payload.get('city_label', 'n/a')})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Closed beta launch readiness")
    parser.add_argument("--base-url", required=True, help="Live API base URL (staging or local)")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip local file/alembic checks")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print("Beta launch readiness check")
    failed = False

    if not args.skip_preflight:
        code = _run([sys.executable, str(ROOT / "scripts" / "go_live_preflight.py")])
        if code != 0:
            failed = True
    else:
        print("  skip local preflight")

    code = _run([sys.executable, str(ROOT / "scripts" / "smoke_deploy.py"), base])
    if code != 0:
        failed = True

    ok_beta, beta_msg = _validate_beta_config(base)
    if ok_beta:
        print(f"  ok {beta_msg}")
    else:
        failed = True
        print(f"  FAIL {beta_msg}")

    print("\n--- Manual steps before inviting beta users ---")
    print("1. Fill escalation contacts in beta/SUPPORT_PLAYBOOK.md")
    print("2. Run rollback drill: npm run rollback:drill -- --base-url", base)
    print("3. Fill launch/GO_LIVE_SIGNOFF.md (npm run release:metadata for git/alembic fields)")
    print("4. Share beta scope: categories electrical/plumbing/cleaning; PINs 248001, 110001, 560001")
    print("5. Monitor KPIs: GET /api/beta/kpis (admin JWT)")

    if failed:
        print("\nBeta launch check FAILED.")
        return 1

    print("\nBeta launch check passed — safe to invite first beta cohort.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

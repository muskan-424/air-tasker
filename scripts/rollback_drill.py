#!/usr/bin/env python3
"""Staging rollback drill helper (Phase Z).

Verifies smoke passes, prints rollback commands, optionally re-runs smoke after rollback.

Usage:
  python scripts/rollback_drill.py
  python scripts/rollback_drill.py --base-url http://localhost:4000 --verify-after
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_smoke(base_url: str) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "smoke_deploy.py"), base_url]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def print_rollback_playbook(previous_tag: str) -> None:
    print("\n--- Rollback playbook (execute on staging first) ---")
    print("1. Announce rollback start to release owner + rollback owner.")
    print("2. Stop current stack:")
    print("   docker compose -f docker-compose.yml -f docker-compose.staging.yml down")
    print(f"3. Check out last known good release (example tag): git checkout {previous_tag}")
    print("4. Restore previous env snapshot / secrets if changed in bad deploy.")
    print("5. Start stack:")
    print("   docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build -d")
    print("6. Verify migration state:")
    print("   docker compose exec api alembic current")
    print("7. Run smoke + go-live watch (short):")
    print("   python scripts/smoke_deploy.py http://localhost:4000")
    print("   python scripts/go_live_watch.py --minutes 5 --interval 30")
    print("8. Document incident timeline and keep bad release tag for RCA.")
    print("--- end playbook ---\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback drill for staging/production readiness")
    parser.add_argument("--base-url", default="http://localhost:4000")
    parser.add_argument("--previous-tag", default="v0.9.0-staging")
    parser.add_argument(
        "--verify-after",
        action="store_true",
        help="Run smoke again after printing rollback steps (assumes operator rolled back manually)",
    )
    args = parser.parse_args()

    print("Step 1/3: baseline smoke (pre-rollback state)")
    if run_smoke(args.base_url) != 0:
        print("Baseline smoke failed — fix staging before rollback drill.", file=sys.stderr)
        return 1

    print("\nStep 2/3: rollback commands")
    print_rollback_playbook(args.previous_tag)

    if args.verify_after:
        input("Press Enter after completing rollback steps to run post-rollback smoke...")
        print("Step 3/3: post-rollback smoke")
        if run_smoke(args.base_url) != 0:
            print("Post-rollback smoke failed.", file=sys.stderr)
            return 1

    print("Rollback drill helper completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

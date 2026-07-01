#!/usr/bin/env python3
"""Local go-live preflight checks (Phase Z).

Validates repo artifacts and optional live API health before a release window.

Usage:
  python scripts/go_live_preflight.py
  python scripts/go_live_preflight.py --base-url http://localhost:4000
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "launch/GO_LIVE_SIGNOFF.md",
    "launch/ROLLBACK_DRILL.md",
    "launch/FIRST_60_MINUTES.md",
    "launch/CHANGE_FREEZE_COMMS.md",
    ".env.production.example",
    "docker-compose.prod.yml",
    "scripts/smoke_deploy.py",
    "scripts/go_live_watch.py",
    "scripts/rollback_drill.py",
]


def check_files() -> list[str]:
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    return missing


def check_alembic_head() -> tuple[bool, str]:
    versions_dir = ROOT / "backend_fastapi" / "alembic" / "versions"
    if not versions_dir.is_dir():
        return False, "alembic versions directory missing"

    revisions: dict[str, str | None] = {}
    for path in versions_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        rev_match = re.search(r'^revision:\s*str\s*=\s*["\']([^"\']+)["\']', text, re.M)
        down_match = re.search(r'^down_revision:.*=\s*(?:\(([^)]+)\)|["\']([^"\']*)["\']|None)', text, re.M)
        if not rev_match:
            continue
        rev = rev_match.group(1)
        down_raw = down_match.group(1) or down_match.group(2) if down_match else None
        if down_raw:
            down = down_raw.strip().strip('"').strip("'").split(",")[0].strip().strip('"').strip("'")
            if down == "None":
                down = None
        else:
            down = None
        revisions[rev] = down

    if not revisions:
        return False, "no alembic revisions found"

    referenced = {d for d in revisions.values() if d}
    heads = [rev for rev in revisions if rev not in referenced]
    if len(heads) != 1:
        return False, f"expected one alembic head, found {heads}"
    return True, heads[0]


def run_smoke(base_url: str) -> tuple[bool, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "smoke_deploy.py"), base_url]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "smoke failed").strip()
        return False, detail.splitlines()[-1][:200]
    return True, "smoke passed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Go-live preflight checks")
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional API base URL to run smoke_deploy.py against",
    )
    args = parser.parse_args()

    print("Go-live preflight")
    failed = False

    missing = check_files()
    if missing:
        failed = True
        print(f"  FAIL missing files: {', '.join(missing)}")
    else:
        print(f"  ok launch kit ({len(REQUIRED_FILES)} files)")

    ok_head, head_msg = check_alembic_head()
    if ok_head:
        print(f"  ok alembic head={head_msg}")
    else:
        failed = True
        print(f"  FAIL alembic: {head_msg}")

    if args.base_url:
        ok_smoke, smoke_msg = run_smoke(args.base_url.rstrip("/"))
        if ok_smoke:
            print(f"  ok {smoke_msg} ({args.base_url})")
        else:
            failed = True
            print(f"  FAIL smoke: {smoke_msg}")
    else:
        print("  skip live smoke (pass --base-url to verify a running API)")

    if failed:
        print("\nPreflight FAILED — resolve items above before go-live signoff.")
        return 1

    print("\nPreflight passed. Next: fill launch/GO_LIVE_SIGNOFF.md and run rollback drill on staging.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

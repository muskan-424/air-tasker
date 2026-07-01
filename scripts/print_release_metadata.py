#!/usr/bin/env python3
"""Print release metadata for launch/GO_LIVE_SIGNOFF.md (Phase Z).

Usage:
  python scripts/print_release_metadata.py
  python scripts/print_release_metadata.py --tag v1.0.0-beta
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def alembic_head() -> str:
    versions_dir = ROOT / "backend_fastapi" / "alembic" / "versions"
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
    referenced = {d for d in revisions.values() if d}
    heads = [rev for rev in revisions if rev not in referenced]
    return heads[0] if len(heads) == 1 else ", ".join(heads)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print go-live signoff metadata")
    parser.add_argument("--tag", default="", help="Optional release tag to suggest")
    args = parser.parse_args()

    commit = _git("rev-parse", "HEAD")
    short = _git("rev-parse", "--short", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    describe = _git("describe", "--tags", "--always", "--dirty")
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    head = alembic_head()
    tag = args.tag or describe or short

    print("Copy into launch/GO_LIVE_SIGNOFF.md:\n")
    print("| Field | Value |")
    print("|-------|-------|")
    print(f"| **Release version / git tag** | `{tag}` |")
    print(f"| **Git commit** | `{commit}` (`{short}` on `{branch}`) |")
    print(f"| **Alembic head** | `{head}` |")
    print(f"| **Prepared at** | {now} |")
    print(f"| **Linked PRs / changelog** | PR #18 Phase S ratings; main @ {short} |")
    print("\nNext commands:")
    print("  npm run go-live:preflight -- --base-url https://YOUR_STAGING_API")
    print("  npm run beta:check -- --base-url https://YOUR_STAGING_API")
    print("  npm run rollback:drill -- --base-url https://YOUR_STAGING_API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

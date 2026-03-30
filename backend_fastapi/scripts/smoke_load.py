"""Concurrent GET / smoke (stdlib only). Usage: python scripts/smoke_load.py http://127.0.0.1:4000 20"""

from __future__ import annotations

import asyncio
import sys
import urllib.request


async def _get(url: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: urllib.request.urlopen(url, timeout=30).read())


async def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4000/"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    url = base if base.endswith("/") else base + "/"
    await asyncio.gather(*[_get(url) for _ in range(n)])
    print(f"Done {n} GET {url}")


if __name__ == "__main__":
    asyncio.run(main())

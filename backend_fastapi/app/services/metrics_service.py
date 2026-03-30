from __future__ import annotations

from collections import defaultdict
from threading import Lock

_lock = Lock()
_counters: defaultdict[str, int] = defaultdict(int)


def inc(name: str, n: int = 1) -> None:
    with _lock:
        _counters[name] += n


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)

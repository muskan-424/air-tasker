from __future__ import annotations

from collections import defaultdict
from threading import Lock

from app.core.config import settings

_lock = Lock()
_counters: defaultdict[str, int] = defaultdict(int)

# HTTP volume is exported with labels via MetricsMiddleware (prometheus_metrics.HTTP_*).
_PROMETHEUS_SKIP = frozenset({"http_requests_total"})


def inc(name: str, n: int = 1) -> None:
    with _lock:
        _counters[name] += n
    if settings.enable_prometheus_metrics and name not in _PROMETHEUS_SKIP:
        from app.services.prometheus_metrics import business_counter

        business_counter(name).inc(n)


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)

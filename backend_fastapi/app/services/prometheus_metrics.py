"""Prometheus collectors for VayuTask AI (Phase V observability)."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "vayutask_http_requests_total",
    "HTTP requests by method and status code",
    ["method", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "vayutask_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_5XX = Counter(
    "vayutask_http_responses_5xx_total",
    "HTTP 5xx responses",
    ["method"],
)

JOB_QUEUE_DEPTH = Gauge(
    "vayutask_job_queue_depth",
    "Pending in-process background jobs",
)

# Mirrors app.services.metrics_service inc() names (sanitized for Prometheus).
BUSINESS_COUNTERS: dict[str, Counter] = {}


def business_counter(name: str) -> Counter:
    key = name.replace("-", "_")
    if key not in BUSINESS_COUNTERS:
        BUSINESS_COUNTERS[key] = Counter(
            f"vayutask_{key}",
            f"VayuTask business counter ({name})",
        )
    return BUSINESS_COUNTERS[key]

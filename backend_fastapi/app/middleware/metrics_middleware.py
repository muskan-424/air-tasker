import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.services.metrics_service import inc


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inc("http_requests_total")
        start = time.perf_counter()
        response = await call_next(request)
        if settings.enable_prometheus_metrics:
            from app.services.prometheus_metrics import (
                HTTP_5XX,
                HTTP_REQUEST_DURATION,
                HTTP_REQUESTS,
            )

            method = request.method
            status = str(response.status_code)
            HTTP_REQUESTS.labels(method=method, status=status).inc()
            HTTP_REQUEST_DURATION.labels(method=method).observe(time.perf_counter() - start)
            if response.status_code >= 500:
                HTTP_5XX.labels(method=method).inc()
        return response

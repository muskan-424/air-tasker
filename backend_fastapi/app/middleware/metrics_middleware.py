from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.services.metrics_service import inc


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inc("http_requests_total")
        return await call_next(request)

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.metrics_service import snapshot
from app.services.notification_service import notification_delivery_stats
from app.services.kyc_metrics_service import kyc_snapshot
from app.services.payments_metrics_service import payments_snapshot
from app.workers.job_queue import queue_depth

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/prometheus")
async def metrics_prometheus():
    """Prometheus text exposition (also mounted at GET /metrics for scrapers)."""
    if not settings.enable_prometheus_metrics:
        return Response(content="Prometheus metrics disabled\n", media_type="text/plain", status_code=404)

    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    from app.services.prometheus_metrics import JOB_QUEUE_DEPTH

    JOB_QUEUE_DEPTH.set(queue_depth())
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/internal/summary")
async def metrics_summary(_admin: User = Depends(get_current_admin_user)):
    return {"counters": snapshot()}


@router.get("/internal/notifications")
async def metrics_notifications(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    _ = _admin
    stats = await notification_delivery_stats(db)
    return {
        **stats,
        "retry_config": {
            "interval_seconds": settings.notification_retry_interval_seconds,
            "batch_size": settings.notification_retry_batch_size,
            "max_attempts": settings.notification_retry_max_attempts,
        },
    }


@router.get("/internal/kyc")
async def metrics_kyc(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    _ = _admin
    return await kyc_snapshot(db)


@router.get("/internal/payments")
async def metrics_payments(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    _ = _admin
    return {
        **(await payments_snapshot(db)),
        "webhook_cleanup_config": {
            "retention_days": settings.razorpay_webhook_events_retention_days,
            "interval_hours": settings.razorpay_webhook_events_cleanup_interval_hours,
        },
    }

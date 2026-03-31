from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_admin_user, get_user_agent
from app.db.session import get_db
from app.models.user import User
from app.services.audit_service import write_audit
from app.services.notification_service import notification_delivery_stats, retry_failed_notifications
from app.services.razorpay_webhook_cleanup import purge_old_razorpay_webhook_events
from app.workers.job_queue import enqueue

router = APIRouter(prefix="/api/admin/jobs", tags=["admin-jobs"])


class EnqueueBody(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)


class NotificationRetryBody(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=500)


class RazorpayWebhookPurgeBody(BaseModel):
    retention_days: int | None = Field(default=None, ge=1, le=3650)


@router.post("/enqueue")
async def enqueue_job(
    request: Request,
    body: EnqueueBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    await write_audit(
        db,
        user_id=admin.id,
        action="admin_job_enqueue",
        resource_type="job_queue",
        meta={"kind": body.kind, "payload": body.payload},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    await enqueue(body.kind, body.payload)
    return {"status": "queued"}


@router.post("/notifications/retry-failed")
async def retry_failed_notifications_job(
    request: Request,
    body: NotificationRetryBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    payload = {}
    if body.limit is not None:
        payload["limit"] = body.limit
    await write_audit(
        db,
        user_id=admin.id,
        action="admin_notification_retry_enqueue",
        resource_type="notifications",
        meta={"kind": "notifications.retry_failed", "payload": payload},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    await enqueue("notifications.retry_failed", payload)
    return {"status": "queued", "kind": "notifications.retry_failed", "payload": payload}


@router.post("/notifications/retry-failed/sync")
async def retry_failed_notifications_sync(
    request: Request,
    body: NotificationRetryBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Run email retry immediately (bypasses queue). Use for ops/debug; prefer queued path in production."""
    retried = await retry_failed_notifications(db, limit=body.limit)
    stats = await notification_delivery_stats(db)
    await write_audit(
        db,
        user_id=admin.id,
        action="admin_notification_retry_sync",
        resource_type="notifications",
        meta={
            "limit": body.limit,
            "email_delivered_this_run": retried,
            "snapshot": stats,
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {
        "status": "ok",
        "email_delivered_this_run": retried,
        "snapshot": stats,
    }


@router.post("/payments/razorpay-webhooks/purge")
async def purge_razorpay_webhook_events(
    request: Request,
    body: RazorpayWebhookPurgeBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    retention_days = body.retention_days or 90
    deleted = await purge_old_razorpay_webhook_events(db, retention_days=retention_days)
    await write_audit(
        db,
        user_id=admin.id,
        action="admin_razorpay_webhook_purge",
        resource_type="payments",
        meta={"retention_days": retention_days, "deleted_rows": deleted},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"status": "ok", "retention_days": retention_days, "deleted_rows": deleted}

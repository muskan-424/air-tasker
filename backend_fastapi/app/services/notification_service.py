from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.platform_security import Notification, NotificationCategory, NotificationPreference
from app.models.user import User
from app.services.email_service import send_email
from app.services.metrics_service import inc
from app.services.notification_broadcast import broadcast_notification_event

logger = logging.getLogger(__name__)


async def get_or_create_prefs(db: AsyncSession, user_id: uuid.UUID) -> NotificationPreference:
    row = (await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))).scalar_one_or_none()
    if row:
        return row
    row = NotificationPreference(user_id=user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    category: NotificationCategory,
    payload: dict | None = None,
) -> Notification:
    inc("notifications_created_total")
    prefs = await get_or_create_prefs(db, user_id)
    n = Notification(
        user_id=user_id,
        title=title,
        body=body,
        category=category.value,
        payload=payload,
        delivery_status="delivered",
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        return n

    if prefs.email_enabled and _wants_email_for_category(prefs, category):
        inc("notifications_email_attempted_total")
        try:
            await send_email(user.email, title, body)
            n.delivery_status = "delivered"
            inc("notifications_email_delivered_total")
        except Exception as exc:
            # Keep in-app record and mark email delivery failure for worker retries.
            n.delivery_status = "failed"
            inc("notifications_email_failed_total")
            retry_meta = dict(n.payload or {})
            retry_meta["retry_count"] = int(retry_meta.get("retry_count", 0))
            retry_meta["last_error"] = str(exc)[:500]
            n.payload = retry_meta
            logger.exception("notification email send failed id=%s", n.id)
        await db.commit()
        await db.refresh(n)

    await broadcast_notification_event(
        user_id,
        {
            "type": "notification",
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "category": n.category,
            "delivery_status": n.delivery_status,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        },
    )

    return n


def _wants_email_for_category(prefs: NotificationPreference, category: NotificationCategory) -> bool:
    if category == NotificationCategory.TASK:
        return prefs.email_task
    if category == NotificationCategory.ESCROW:
        return prefs.email_escrow
    if category == NotificationCategory.DISPUTE:
        return prefs.email_dispute
    return True


async def retry_failed_notifications(db: AsyncSession, *, limit: int | None = None) -> int:
    batch_size = limit or settings.notification_retry_batch_size
    rows = (
        await db.execute(
            select(Notification)
            .where(Notification.delivery_status == "failed")
            .order_by(Notification.created_at.asc())
            .limit(max(1, min(batch_size, 500)))
        )
    ).scalars().all()
    retried = 0
    for n in rows:
        payload = dict(n.payload or {})
        attempts = int(payload.get("retry_count", 0))
        if attempts >= settings.notification_retry_max_attempts:
            n.delivery_status = "permanent_failure"
            inc("notifications_retry_permanent_failure_total")
            db.add(n)
            continue

        user = (await db.execute(select(User).where(User.id == n.user_id))).scalar_one_or_none()
        if not user:
            n.delivery_status = "permanent_failure"
            inc("notifications_retry_permanent_failure_total")
            db.add(n)
            continue

        prefs = await get_or_create_prefs(db, user.id)
        try:
            category = NotificationCategory(n.category)
        except ValueError:
            category = NotificationCategory.SYSTEM

        if not (prefs.email_enabled and _wants_email_for_category(prefs, category)):
            n.delivery_status = "skipped"
            inc("notifications_retry_skipped_total")
            db.add(n)
            continue

        try:
            inc("notifications_retry_attempted_total")
            await send_email(user.email, n.title, n.body)
            n.delivery_status = "delivered"
            inc("notifications_retry_succeeded_total")
            payload["retry_count"] = attempts + 1
            payload.pop("last_error", None)
            n.payload = payload
            retried += 1
        except Exception as exc:
            inc("notifications_retry_failed_total")
            payload["retry_count"] = attempts + 1
            payload["last_error"] = str(exc)[:500]
            n.payload = payload
            n.delivery_status = (
                "permanent_failure"
                if payload["retry_count"] >= settings.notification_retry_max_attempts
                else "failed"
            )
            if n.delivery_status == "permanent_failure":
                inc("notifications_retry_permanent_failure_total")
            logger.exception("notification retry failed id=%s", n.id)
        db.add(n)

    await db.commit()
    return retried


async def notification_delivery_stats(db: AsyncSession) -> dict[str, object]:
    rows = (await db.execute(select(Notification.delivery_status, func.count()).group_by(Notification.delivery_status))).all()
    by_status = {status: int(count) for status, count in rows}
    total = sum(by_status.values())
    return {
        "by_status": by_status,
        "total": total,
        "pending_retry": by_status.get("failed", 0),
    }

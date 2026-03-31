from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_security import RazorpayWebhookEvent
from app.services.metrics_service import inc

logger = logging.getLogger(__name__)


async def purge_old_razorpay_webhook_events(db: AsyncSession, *, retention_days: int) -> int:
    """Delete dedupe rows older than retention_days. Returns rows deleted."""
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = await db.execute(delete(RazorpayWebhookEvent).where(RazorpayWebhookEvent.created_at < cutoff))
    await db.commit()
    n = int(result.rowcount or 0)
    if n:
        inc("razorpay_webhook_events_purged_total", n)
        logger.info("Purged %s razorpay_webhook_events rows older than %s days", n, retention_days)
    return n

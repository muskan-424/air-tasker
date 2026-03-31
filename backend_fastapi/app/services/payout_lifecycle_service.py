"""
RazorpayX payout lifecycle: webhook sync + status on `escrow_payments.razorpay_payout_status`.

See: https://razorpay.com/docs/webhooks/payouts/
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment
from app.services.metrics_service import inc

logger = logging.getLogger(__name__)

_PAYOUT_DOWNTIME_EVENTS = frozenset({"payout.downtime.started", "payout.downtime.resolved"})


async def sync_payout_escrow_from_webhook(
    db: AsyncSession,
    *,
    event_type: str | None,
    payload: dict,
    razorpay_event_id: str | None,
) -> dict | None:
    """
    Handle Razorpay `payout.*` webhook events. Returns a response dict if handled, or None if not a payout event.
    """
    if not event_type or not event_type.startswith("payout."):
        return None

    if event_type in _PAYOUT_DOWNTIME_EVENTS:
        logger.info("Ignoring Razorpay global payout event %s", event_type)
        if razorpay_event_id:
            await db.commit()
        return {"status": "ok", "note": "payout_downtime_ignored"}

    payout = (payload.get("payout") or {}).get("entity") or {}
    payout_id = payout.get("id")
    if not payout_id:
        if razorpay_event_id:
            await db.commit()
        return {"status": "ignored", "reason": "missing payout id"}

    escrow = (
        await db.execute(select(EscrowPayment).where(EscrowPayment.razorpay_payout_id == payout_id))
    ).scalar_one_or_none()
    if not escrow:
        logger.info("Razorpay payout webhook: no escrow for payout_id=%s", payout_id)
        if razorpay_event_id:
            await db.commit()
        return {"status": "ok", "note": "no matching escrow"}

    raw_status = (payout.get("status") or "").strip().lower()
    prev = (escrow.razorpay_payout_status or "").strip().lower()

    if prev in ("processed", "reversed") and event_type in ("payout.failed", "payout.rejected"):
        logger.warning(
            "Razorpay payout anomaly: %s after terminal state escrow=%s prev=%s",
            event_type,
            escrow.id,
            prev,
        )

    if raw_status:
        escrow.razorpay_payout_status = raw_status[:32]
        db.add(escrow)

    if event_type == "payout.processed":
        et = EscrowEventType.PAYOUT_PROCESSED
        inc("razorpay_webhook_payout_processed_total")
    elif event_type == "payout.failed":
        et = EscrowEventType.PAYOUT_FAILED
        inc("razorpay_webhook_payout_failed_total")
    elif event_type == "payout.reversed":
        et = EscrowEventType.PAYOUT_REVERSED
        inc("razorpay_webhook_payout_reversed_total")
    else:
        et = EscrowEventType.PAYOUT_UPDATED
        inc("razorpay_webhook_payout_updated_total")

    db.add(
        EscrowEvent(
            escrow_payment_id=escrow.id,
            type=et,
            metadata_json={"source": "razorpay_webhook", "event": event_type, "payout": payout},
        )
    )
    await db.commit()
    return {"status": "ok", "escrow_id": str(escrow.id)}

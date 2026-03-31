from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_security import RazorpayWebhookEvent
from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment


async def payments_snapshot(db: AsyncSession) -> dict[str, object]:
    total_escrows = int((await db.execute(select(func.count()).select_from(EscrowPayment))).scalar_one() or 0)
    with_order = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowPayment).where(EscrowPayment.razorpay_order_id.is_not(None))
            )
        ).scalar_one()
        or 0
    )
    with_payment = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowPayment).where(EscrowPayment.razorpay_payment_id.is_not(None))
            )
        ).scalar_one()
        or 0
    )
    with_refund = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowPayment).where(EscrowPayment.razorpay_refund_id.is_not(None))
            )
        ).scalar_one()
        or 0
    )
    with_payout = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowPayment).where(EscrowPayment.razorpay_payout_id.is_not(None))
            )
        ).scalar_one()
        or 0
    )
    payout_status_processed = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowPayment).where(EscrowPayment.razorpay_payout_status == "processed")
            )
        ).scalar_one()
        or 0
    )
    payout_status_failed = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowPayment).where(EscrowPayment.razorpay_payout_status == "failed")
            )
        ).scalar_one()
        or 0
    )
    captured_events = int(
        (
            await db.execute(
                select(func.count()).select_from(EscrowEvent).where(EscrowEvent.type == EscrowEventType.PAYMENT_CAPTURED)
            )
        ).scalar_one()
        or 0
    )
    webhook_events_total = int((await db.execute(select(func.count()).select_from(RazorpayWebhookEvent))).scalar_one() or 0)
    recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
    webhook_events_24h = int(
        (
            await db.execute(
                select(func.count()).select_from(RazorpayWebhookEvent).where(RazorpayWebhookEvent.created_at >= recent_cutoff)
            )
        ).scalar_one()
        or 0
    )

    return {
        "escrow_total": total_escrows,
        "escrow_with_razorpay_order_id": with_order,
        "escrow_with_razorpay_payment_id": with_payment,
        "escrow_with_razorpay_refund_id": with_refund,
        "escrow_with_razorpay_payout_id": with_payout,
        "escrow_payout_status_processed": payout_status_processed,
        "escrow_payout_status_failed": payout_status_failed,
        "payment_captured_events": captured_events,
        "webhook_events_total": webhook_events_total,
        "webhook_events_last_24h": webhook_events_24h,
    }

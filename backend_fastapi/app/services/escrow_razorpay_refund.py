from __future__ import annotations

import logging
import uuid
from decimal import Decimal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment
from app.services.metrics_service import inc
from app.services.razorpay_service import refund_payment

logger = logging.getLogger(__name__)


async def try_refund_escrow_capture(
    db: AsyncSession,
    escrow: EscrowPayment,
    *,
    dispute_id: uuid.UUID | None = None,
    partial_amount_inr: Decimal | None = None,
) -> bool:
    """
    Call Razorpay refund when a captured payment exists and no refund was recorded yet.
    Returns True if a new refund was issued and persisted on this escrow row.
    Returns False if skipped (already refunded, no payment id, or Razorpay keys not configured).
    Raises httpx.HTTPStatusError on Razorpay API failure when a refund was attempted.
    """
    if escrow.razorpay_refund_id:
        return False
    if not escrow.razorpay_payment_id:
        return False
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        logger.warning(
            "Razorpay keys not set; skipping refund for escrow_id=%s payment_id=%s",
            escrow.id,
            escrow.razorpay_payment_id,
        )
        return False

    amount_paise: int | None = None
    if partial_amount_inr is not None:
        amount_paise = int((partial_amount_inr * Decimal(100)).quantize(Decimal("1")))

    rp = await refund_payment(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        payment_id=escrow.razorpay_payment_id,
        amount_paise=amount_paise,
    )
    refund_id = rp["id"]
    escrow.razorpay_refund_id = refund_id
    db.add(escrow)
    meta: dict = {
        "refund_id": refund_id,
        "razorpay": {
            "id": rp.get("id"),
            "amount": rp.get("amount"),
            "status": rp.get("status"),
            "created_at": rp.get("created_at"),
        },
    }
    if dispute_id is not None:
        meta["resolved_dispute_id"] = str(dispute_id)
    db.add(
        EscrowEvent(
            escrow_payment_id=escrow.id,
            type=EscrowEventType.REFUND_ISSUED,
            metadata_json=meta,
        )
    )
    inc("razorpay_refunds_total")
    return True

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.platform_security import RazorpayWebhookEvent
from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment
from app.services.metrics_service import inc
from app.services.payout_lifecycle_service import sync_payout_escrow_from_webhook
from app.services.razorpay_service import verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature")

    if settings.razorpay_webhook_secret:
        if not verify_webhook_signature(body, sig, settings.razorpay_webhook_secret):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    else:
        if settings.environment.lower() not in {"development", "dev", "test"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook secret is required outside development/test",
            )
        logger.warning("RAZORPAY_WEBHOOK_SECRET not set; accepting webhook without signature verification")

    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_type = data.get("event")
    razorpay_event_id = data.get("id")

    if razorpay_event_id:
        ins = (
            insert(RazorpayWebhookEvent)
            .values(
                id=uuid.uuid4(),
                razorpay_event_id=razorpay_event_id,
                event_type=event_type or "unknown",
            )
            .on_conflict_do_nothing(index_elements=["razorpay_event_id"])
            .returning(RazorpayWebhookEvent.id)
        )
        res = await db.execute(ins)
        if res.scalar_one_or_none() is None:
            inc("razorpay_webhook_duplicate_total")
            return {"status": "ok", "note": "duplicate event"}
    else:
        logger.warning("Razorpay webhook payload missing top-level id; replay dedupe skipped")

    if event_type == "payment.captured":
        payload = data.get("payload") or {}
        payment = (payload.get("payment") or {}).get("entity") or {}
        order_id = payment.get("order_id")
        payment_id = payment.get("id")
        if not order_id or not payment_id:
            if razorpay_event_id:
                await db.commit()
            return {"status": "ignored", "reason": "missing order_id or payment_id"}

        escrow = (
            await db.execute(select(EscrowPayment).where(EscrowPayment.razorpay_order_id == order_id))
        ).scalar_one_or_none()
        if not escrow:
            logger.info("Razorpay webhook: no escrow for order_id=%s", order_id)
            if razorpay_event_id:
                await db.commit()
            return {"status": "ok", "note": "no matching escrow"}

        if escrow.razorpay_payment_id:
            if razorpay_event_id:
                await db.commit()
            return {"status": "ok", "note": "already recorded"}

        escrow.razorpay_payment_id = payment_id
        db.add(
            EscrowEvent(
                escrow_payment_id=escrow.id,
                type=EscrowEventType.PAYMENT_CAPTURED,
                metadata_json={"razorpay_payment_id": payment_id, "payment": payment},
            )
        )
        await db.commit()
        inc("razorpay_webhook_payment_captured_total")
        return {"status": "ok", "escrow_id": str(escrow.id)}

    if event_type == "refund.processed":
        payload = data.get("payload") or {}
        refund = (payload.get("refund") or {}).get("entity") or {}
        refund_id = refund.get("id")
        payment_id = refund.get("payment_id")
        if not refund_id or not payment_id:
            if razorpay_event_id:
                await db.commit()
            return {"status": "ignored", "reason": "missing refund_id or payment_id"}

        escrow = (
            await db.execute(select(EscrowPayment).where(EscrowPayment.razorpay_payment_id == payment_id))
        ).scalar_one_or_none()
        if not escrow:
            logger.info("Razorpay webhook: no escrow for refund payment_id=%s", payment_id)
            if razorpay_event_id:
                await db.commit()
            return {"status": "ok", "note": "no matching escrow"}

        if escrow.razorpay_refund_id:
            if escrow.razorpay_refund_id != refund_id:
                logger.warning(
                    "Escrow %s refund id mismatch: stored=%s webhook=%s",
                    escrow.id,
                    escrow.razorpay_refund_id,
                    refund_id,
                )
            if razorpay_event_id:
                await db.commit()
            return {"status": "ok", "note": "already recorded"}

        escrow.razorpay_refund_id = refund_id
        db.add(
            EscrowEvent(
                escrow_payment_id=escrow.id,
                type=EscrowEventType.REFUND_ISSUED,
                metadata_json={"source": "razorpay_webhook", "refund": refund},
            )
        )
        await db.commit()
        inc("razorpay_webhook_refund_processed_total")
        return {"status": "ok", "escrow_id": str(escrow.id)}

    if event_type == "refund.failed":
        payload = data.get("payload") or {}
        refund = (payload.get("refund") or {}).get("entity") or {}
        payment_id = refund.get("payment_id")
        logger.warning(
            "Razorpay refund.failed payment_id=%s refund_id=%s",
            payment_id,
            refund.get("id"),
        )
        inc("razorpay_webhook_refund_failed_total")
        if razorpay_event_id:
            await db.commit()
        return {"status": "ok", "note": "refund_failed_logged"}

    payout_resp = await sync_payout_escrow_from_webhook(
        db,
        event_type=event_type,
        payload=data.get("payload") or {},
        razorpay_event_id=razorpay_event_id,
    )
    if payout_resp is not None:
        return payout_resp

    if razorpay_event_id:
        await db.commit()
    return {"status": "ignored", "event": event_type}

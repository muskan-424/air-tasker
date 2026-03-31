import httpx
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.services.kyc_service import user_has_verified_kyc
from app.db.session import get_db
from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment, EscrowStatus, Task
from app.models.user import User, UserRole
from app.schemas.payments import (
    EscrowPayoutInitiateRequest,
    EscrowPayoutInitiateResponse,
    RazorpayOrderRequest,
    RazorpayOrderResponse,
    RazorpayRefundRequest,
    RazorpayRefundResponse,
    RegisterBankPayoutRequest,
    RegisterBankPayoutResponse,
)
from app.services.escrow_razorpay_refund import try_refund_escrow_capture
from app.services.metrics_service import inc
from app.services.razorpay_service import create_order
from app.services.tasker_escrow_payout import register_tasker_bank_for_payout, try_escrow_payout_to_tasker

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/razorpay/order", response_model=RazorpayOrderResponse)
async def create_razorpay_order_for_task(
    body: RazorpayOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Razorpay is not configured (set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)",
        )

    task = (await db.execute(select(Task).where(Task.id == body.task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.id != task.poster_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only poster can fund escrow")

    escrow_result = await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))
    escrow = escrow_result.scalar_one_or_none()
    if not escrow:
        amount = task.suggested_price_max or task.suggested_price_min or Decimal("1000.00")
        escrow = EscrowPayment(task_id=task.id, status=EscrowStatus.HELD, amount=amount, currency="INR")
        db.add(escrow)
        await db.flush()
        db.add(
            EscrowEvent(
                escrow_payment_id=escrow.id,
                type=EscrowEventType.HELD,
                metadata_json={"source": "razorpay_order"},
            )
        )
        await db.commit()
        await db.refresh(escrow)

    if escrow.razorpay_order_id:
        amount_paise = int((escrow.amount * Decimal(100)).quantize(Decimal("1")))
        inc("razorpay_order_idempotent_total")
        return RazorpayOrderResponse(
            order_id=escrow.razorpay_order_id,
            amount=str(escrow.amount),
            amount_paise=amount_paise,
            currency=escrow.currency,
            key_id=settings.razorpay_key_id,
            escrow_id=str(escrow.id),
            task_id=str(task.id),
        )

    rp = await create_order(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        amount_inr=escrow.amount,
        receipt=str(task.id).replace("-", "")[:32],
        notes={"task_id": str(task.id), "escrow_id": str(escrow.id)},
    )
    order_id = rp["id"]
    escrow.razorpay_order_id = order_id
    db.add(escrow)
    await db.commit()
    await db.refresh(escrow)
    inc("razorpay_orders_created_total")

    return RazorpayOrderResponse(
        order_id=order_id,
        amount=str(escrow.amount),
        amount_paise=int(rp["amount"]),
        currency=rp.get("currency", "INR"),
        key_id=settings.razorpay_key_id,
        escrow_id=str(escrow.id),
        task_id=str(task.id),
    )


@router.post("/razorpay/refund", response_model=RazorpayRefundResponse)
async def manual_razorpay_refund_for_escrow(
    body: RazorpayRefundRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin/reviewer retry or manual refund when escrow was cancelled without a recorded refund."""
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or reviewer can issue refunds")

    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Razorpay is not configured (set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)",
        )

    task = (await db.execute(select(Task).where(Task.id == body.task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    escrow = (await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))).scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")

    if escrow.status != EscrowStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Refund only allowed when escrow is CANCELLED (current: {escrow.status.value})",
        )
    if escrow.razorpay_refund_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Refund already recorded for this escrow",
        )

    try:
        issued = await try_refund_escrow_capture(db, escrow, partial_amount_inr=body.amount_inr)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Razorpay refund failed: {e.response.text[:300]}",
        ) from e

    if not issued:
        if not escrow.razorpay_payment_id:
            return RazorpayRefundResponse(issued=False, skipped_reason="no_razorpay_payment_id")
        return RazorpayRefundResponse(issued=False, skipped_reason="refund_not_applicable")

    await db.commit()
    return RazorpayRefundResponse(issued=True, refund_id=escrow.razorpay_refund_id)


@router.post("/razorpay/payout/register-bank", response_model=RegisterBankPayoutResponse)
async def register_razorpay_payout_bank_account(
    body: RegisterBankPayoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tasker links an India bank account via RazorpayX contact + fund account (required before escrow payout)."""
    if current_user.role != UserRole.TASKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only taskers can register payout bank details")

    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Razorpay is not configured (set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)",
        )

    if settings.kyc_required_for_payout and not await user_has_verified_kyc(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification is required before registering bank details for payouts",
        )

    try:
        out = await register_tasker_bank_for_payout(
            db,
            current_user,
            beneficiary_name=body.beneficiary_name.strip(),
            ifsc=body.ifsc,
            account_number=body.account_number,
        )
    except ValueError as e:
        code = str(e)
        if code == "fund_account_already_registered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bank account already registered") from e
        if code == "razorpay_not_configured":
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Razorpay not configured") from e
        if code == "invalid_ifsc":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IFSC must be 11 characters") from e
        if code == "invalid_account_number":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account number must be 9–18 digits",
            ) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from e
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Razorpay error: {e.response.text[:300]}",
        ) from e

    return RegisterBankPayoutResponse(contact_id=out["contact_id"], fund_account_id=out["fund_account_id"])


@router.post("/razorpay/payout/initiate-escrow", response_model=EscrowPayoutInitiateResponse)
async def initiate_escrow_payout_manual(
    body: EscrowPayoutInitiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry Razorpay payout after escrow is RELEASED (e.g. if automatic attempt failed). Admin/reviewer only."""
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or reviewer can initiate payout")

    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Razorpay is not configured",
        )

    task = (await db.execute(select(Task).where(Task.id == body.task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    escrow = (await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))).scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")

    if escrow.status != EscrowStatus.RELEASED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payout only when escrow is RELEASED (current: {escrow.status.value})",
        )

    result = await try_escrow_payout_to_tasker(db, task, escrow)
    return EscrowPayoutInitiateResponse(status=result)

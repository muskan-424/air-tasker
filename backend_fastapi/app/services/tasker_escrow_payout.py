from __future__ import annotations

import logging
import re
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment, Task, TaskAcceptance
from app.models.user import User
from app.services.kyc_service import user_has_verified_kyc
from app.services.metrics_service import inc
from app.services.razorpay_service import create_contact, create_fund_account_bank, create_payout

logger = logging.getLogger(__name__)


def _digits_only(s: str | None) -> str:
    if not s:
        return ""
    return "".join(c for c in s if c.isdigit())


async def try_escrow_payout_to_tasker(db: AsyncSession, task: Task, escrow: EscrowPayment) -> str:
    """
    After escrow is RELEASED, send RazorpayX payout to the accepted tasker's fund account.
    Returns a short status token for API responses (never includes secrets).
    """
    if escrow.razorpay_payout_id:
        return "skipped_already_paid_out"
    if not escrow.razorpay_payment_id:
        return "skipped_no_capture"
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        return "skipped_no_razorpay_keys"
    if not settings.razorpay_payout_account_number:
        logger.warning("RAZORPAY_PAYOUT_ACCOUNT_NUMBER not set; skipping payout for escrow %s", escrow.id)
        return "skipped_no_payout_account_config"

    acc_row = await db.execute(select(TaskAcceptance).where(TaskAcceptance.task_id == task.id))
    acceptance = acc_row.scalar_one_or_none()
    if not acceptance:
        return "skipped_no_acceptance"

    tasker = await db.get(User, acceptance.tasker_id)
    if not tasker or not tasker.razorpay_fund_account_id:
        return "skipped_no_tasker_fund_account"

    if settings.kyc_required_for_payout and not await user_has_verified_kyc(db, tasker.id):
        logger.info("Payout skipped: KYC not verified tasker_id=%s escrow=%s", tasker.id, escrow.id)
        return "skipped_kyc_not_verified"

    amount_paise = int((escrow.amount * Decimal(100)).quantize(Decimal("1")))
    if amount_paise <= 0:
        return "skipped_zero_amount"

    ref = f"escrow_{escrow.id}".replace("-", "")[:40]
    idem = f"payout-{escrow.id}"

    try:
        po = await create_payout(
            key_id=settings.razorpay_key_id,
            key_secret=settings.razorpay_key_secret,
            razorpayx_account_number=settings.razorpay_payout_account_number,
            fund_account_id=tasker.razorpay_fund_account_id,
            amount_paise=amount_paise,
            currency=escrow.currency or "INR",
            reference_id=ref,
            idempotency_key=idem,
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "Razorpay payout failed escrow=%s status=%s body=%s",
            escrow.id,
            e.response.status_code,
            e.response.text[:400],
        )
        return "failed_razorpay"

    payout_id = po.get("id")
    if not payout_id:
        logger.error("Razorpay payout response missing id: %s", po)
        return "failed_invalid_response"

    st = (po.get("status") or "queued").strip().lower()
    escrow.razorpay_payout_status = st[:32] if st else "queued"
    escrow.razorpay_payout_id = payout_id
    db.add(escrow)
    db.add(
        EscrowEvent(
            escrow_payment_id=escrow.id,
            type=EscrowEventType.PAYOUT_INITIATED,
            metadata_json={"razorpay_payout_id": payout_id, "payout": po},
        )
    )
    await db.commit()
    inc("razorpay_payouts_initiated_total")
    return "initiated"


async def register_tasker_bank_for_payout(
    db: AsyncSession,
    user: User,
    *,
    beneficiary_name: str,
    ifsc: str,
    account_number: str,
) -> dict[str, str]:
    """Create Razorpay contact + bank fund account and persist IDs on the user."""
    if user.razorpay_fund_account_id:
        raise ValueError("fund_account_already_registered")
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise ValueError("razorpay_not_configured")

    ifsc_clean = re.sub(r"\s+", "", ifsc).upper()
    if len(ifsc_clean) != 11:
        raise ValueError("invalid_ifsc")

    acct_digits = _digits_only(account_number)
    if len(acct_digits) < 9 or len(acct_digits) > 18:
        raise ValueError("invalid_account_number")

    phone = _digits_only(user.phone) or "9999999999"
    ref = f"user_{user.id}".replace("-", "")[:40]

    contact_id = user.razorpay_contact_id
    if not contact_id:
        cont = await create_contact(
            key_id=settings.razorpay_key_id,
            key_secret=settings.razorpay_key_secret,
            name=beneficiary_name,
            email=user.email,
            phone_digits=phone,
            reference_id=ref,
        )
        contact_id = cont["id"]
        user.razorpay_contact_id = contact_id

    fa = await create_fund_account_bank(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        contact_id=contact_id,
        beneficiary_name=beneficiary_name,
        ifsc=ifsc_clean,
        account_number=acct_digits,
    )
    user.razorpay_fund_account_id = fa["id"]
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"contact_id": contact_id, "fund_account_id": fa["id"]}



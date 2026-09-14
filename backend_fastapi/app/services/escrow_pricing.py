"""Escrow amounts derived from the agreed task price plus service fees."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import EscrowEvent, EscrowEventType, EscrowPayment, EscrowStatus, Task
from app.models.task_collaboration import TaskScope, TaskScopeStatus
from app.services.fee_service import compute_fees

DEFAULT_TASK_PRICE = Decimal("1000.00")


async def agreed_task_price(db: AsyncSession, task: Task) -> Decimal:
    """Accepted offer/scope price, else the AI-suggested budget, else a default."""
    scope = (
        await db.execute(
            select(TaskScope).where(TaskScope.task_id == task.id, TaskScope.status == TaskScopeStatus.ACCEPTED)
        )
    ).scalar_one_or_none()
    if scope:
        return scope.agreed_price
    return task.suggested_price_max or task.suggested_price_min or DEFAULT_TASK_PRICE


async def create_held_escrow(db: AsyncSession, task: Task, *, source: str) -> EscrowPayment:
    """Add a HELD escrow charging the poster price + poster fee. Caller commits."""
    fees = compute_fees(await agreed_task_price(db, task))
    escrow = EscrowPayment(
        task_id=task.id,
        status=EscrowStatus.HELD,
        amount=fees.poster_total,
        currency="INR",
        task_price=fees.task_price,
        poster_fee=fees.poster_fee,
        tasker_fee=fees.tasker_fee,
    )
    db.add(escrow)
    await db.flush()
    db.add(
        EscrowEvent(
            escrow_payment_id=escrow.id,
            type=EscrowEventType.HELD,
            metadata_json={"source": source, "fees": fees.as_dict()},
        )
    )
    return escrow


def tasker_payout_amount(escrow: EscrowPayment) -> Decimal:
    """What the tasker receives; legacy escrows without a fee breakdown pay out the full amount."""
    if escrow.task_price is None:
        return escrow.amount
    return escrow.task_price - (escrow.tasker_fee or Decimal("0.00"))

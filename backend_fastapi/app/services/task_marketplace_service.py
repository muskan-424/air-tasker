"""Offers (taskers quote, poster picks one) and task cancellation with fees and refunds."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.platform_security import NotificationCategory
from app.models.task import (
    AcceptanceStatus,
    Dispute,
    DisputeStatus,
    EscrowEvent,
    EscrowEventType,
    EscrowPayment,
    EscrowStatus,
    Task,
    TaskAcceptance,
    TaskStatus,
)
from app.models.task_collaboration import TaskScope, TaskScopeStatus
from app.models.task_offer import CancelledBy, OfferStatus, TaskCancellation, TaskOffer
from app.models.user import User, UserRole, is_marketplace_user
from app.services.escrow_pricing import agreed_task_price
from app.services.escrow_razorpay_refund import try_refund_escrow_capture
from app.services.fee_service import cancellation_fee
from app.services.notification_service import create_notification

_ACTIVE_STATUSES = {TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS}
# Once work is verified or disputed, cancelling is replaced by the dispute flow.
_ESCROW_BLOCKS_CANCEL = {EscrowStatus.RELEASE_ELIGIBLE, EscrowStatus.DISPUTE_OPENED}


class MarketplaceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


async def _lock_task(db: AsyncSession, task_id: uuid.UUID) -> Task:
    task = (await db.execute(select(Task).where(Task.id == task_id).with_for_update())).scalar_one_or_none()
    if not task:
        raise MarketplaceError("not_found", "Task not found")
    return task


async def _active_acceptance(db: AsyncSession, task_id: uuid.UUID) -> TaskAcceptance | None:
    return (
        await db.execute(
            select(TaskAcceptance).where(
                TaskAcceptance.task_id == task_id,
                TaskAcceptance.status == AcceptanceStatus.ACCEPTED,
            )
        )
    ).scalar_one_or_none()


# ── Offers ────────────────────────────────────────────────────────────────────


async def submit_offer(
    db: AsyncSession, task_id: uuid.UUID, tasker: User, *, amount: Decimal, message: str | None
) -> tuple[TaskOffer, bool]:
    """Create or update the tasker's offer. Returns (offer, created)."""
    if not is_marketplace_user(tasker):
        raise MarketplaceError("forbidden", "Staff accounts cannot make offers")
    task = await _lock_task(db, task_id)
    if task.poster_id == tasker.id:
        raise MarketplaceError("forbidden", "You cannot make an offer on your own task")
    if task.status != TaskStatus.PUBLISHED:
        raise MarketplaceError("conflict", "This task is no longer taking offers")
    if not (Decimal(str(settings.offer_min_inr)) <= amount <= Decimal(str(settings.offer_max_inr))):
        raise MarketplaceError(
            "bad_request",
            f"Offer must be between ₹{settings.offer_min_inr:,.0f} and ₹{settings.offer_max_inr:,.0f}",
        )

    offer = (
        await db.execute(select(TaskOffer).where(TaskOffer.task_id == task.id, TaskOffer.tasker_id == tasker.id))
    ).scalar_one_or_none()
    created = offer is None
    if offer is None:
        offer = TaskOffer(task_id=task.id, tasker_id=tasker.id, amount=amount, message=message)
        db.add(offer)
    else:
        offer.amount = amount
        offer.message = message
        offer.status = OfferStatus.PENDING
    await db.commit()
    await db.refresh(offer)

    await create_notification(
        db,
        user_id=task.poster_id,
        title="New offer on your task" if created else "An offer was updated",
        body=f"A tasker offered ₹{offer.amount} for your {task.category} task.",
        category=NotificationCategory.TASK,
        payload={"task_id": str(task.id), "offer_id": str(offer.id), "event": "offer_submitted"},
    )
    return offer, created


async def withdraw_offer(db: AsyncSession, task_id: uuid.UUID, offer_id: uuid.UUID, user: User) -> TaskOffer:
    offer = (
        await db.execute(select(TaskOffer).where(TaskOffer.id == offer_id, TaskOffer.task_id == task_id))
    ).scalar_one_or_none()
    if not offer:
        raise MarketplaceError("not_found", "Offer not found")
    if offer.tasker_id != user.id:
        raise MarketplaceError("forbidden", "You can only withdraw your own offer")
    if offer.status != OfferStatus.PENDING:
        raise MarketplaceError("conflict", f"Offer is {offer.status.value.lower()} and cannot be withdrawn")
    offer.status = OfferStatus.WITHDRAWN
    await db.commit()
    await db.refresh(offer)
    return offer


async def accept_offer(
    db: AsyncSession, task_id: uuid.UUID, offer_id: uuid.UUID, poster: User
) -> tuple[Task, TaskOffer, TaskAcceptance]:
    """Assign the task to the offer's tasker at the offered price; decline all other offers."""
    task = await _lock_task(db, task_id)
    if task.poster_id != poster.id:
        raise MarketplaceError("forbidden", "Only the poster can accept offers")
    if task.status != TaskStatus.PUBLISHED:
        raise MarketplaceError("conflict", "This task already has a tasker or is closed")

    offers = (await db.execute(select(TaskOffer).where(TaskOffer.task_id == task.id))).scalars().all()
    offer = next((o for o in offers if o.id == offer_id), None)
    if not offer:
        raise MarketplaceError("not_found", "Offer not found")
    if offer.status != OfferStatus.PENDING:
        raise MarketplaceError("conflict", f"Offer is {offer.status.value.lower()}")

    acceptance = (
        await db.execute(
            select(TaskAcceptance).where(TaskAcceptance.task_id == task.id, TaskAcceptance.tasker_id == offer.tasker_id)
        )
    ).scalar_one_or_none()
    if acceptance is None:
        acceptance = TaskAcceptance(task_id=task.id, tasker_id=offer.tasker_id)
        db.add(acceptance)
    acceptance.status = AcceptanceStatus.ACCEPTED
    acceptance.acknowledgement = {"source": "offer", "offer_id": str(offer.id)}

    # The accepted offer is the agreed scope, so escrow is funded at the offered price.
    scope = (await db.execute(select(TaskScope).where(TaskScope.task_id == task.id))).scalar_one_or_none()
    if scope is None:
        scope = TaskScope(task_id=task.id, poster_id=task.poster_id)
        db.add(scope)
    scope.tasker_id = offer.tasker_id
    scope.proposed_by_id = offer.tasker_id
    scope.agreed_price = offer.amount
    scope.currency = offer.currency
    scope.scope_json = {"source": "offer", "offer_id": str(offer.id)}
    scope.note = offer.message
    scope.status = TaskScopeStatus.ACCEPTED
    scope.agreed_at = datetime.now(timezone.utc)

    declined: list[uuid.UUID] = []
    for other in offers:
        if other.id == offer.id:
            other.status = OfferStatus.ACCEPTED
        elif other.status == OfferStatus.PENDING:
            other.status = OfferStatus.DECLINED
            declined.append(other.tasker_id)
    task.status = TaskStatus.ACCEPTED
    await db.commit()
    await db.refresh(acceptance)
    await db.refresh(offer)

    await create_notification(
        db,
        user_id=offer.tasker_id,
        title="Your offer was accepted",
        body=f"You've been assigned the {task.category} task for ₹{offer.amount}.",
        category=NotificationCategory.TASK,
        payload={"task_id": str(task.id), "offer_id": str(offer.id), "event": "offer_accepted"},
    )
    for tasker_id in declined:
        await create_notification(
            db,
            user_id=tasker_id,
            title="Task assigned to another tasker",
            body=f"The {task.category} task you offered on was assigned to someone else.",
            category=NotificationCategory.TASK,
            payload={"task_id": str(task.id), "event": "offer_declined"},
        )
    return task, offer, acceptance


# ── Cancellation ──────────────────────────────────────────────────────────────


async def cancel_task(db: AsyncSession, task_id: uuid.UUID, user: User, *, reason: str | None) -> TaskCancellation:
    """
    Cancel a task.

    - Before assignment: the poster (or an admin) cancels for free; pending offers are declined.
    - After assignment: the poster, the assigned tasker, or an admin. Poster and tasker
      cancellations carry a fee (percent of the task price). A poster's fee is kept from the
      escrow refund; a tasker's fee is recorded against them and the poster is refunded in full.
    - Verified or disputed work cannot be cancelled here; it goes through disputes.
    """
    task = await _lock_task(db, task_id)
    if task.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
        raise MarketplaceError("conflict", f"Task is already {task.status.value.lower()}")

    acceptance = await _active_acceptance(db, task.id)
    if user.role == UserRole.ADMIN:
        actor = CancelledBy.ADMIN
    elif user.id == task.poster_id:
        actor = CancelledBy.POSTER
    elif acceptance is not None and user.id == acceptance.tasker_id:
        actor = CancelledBy.TASKER
    else:
        raise MarketplaceError("forbidden", "Only the poster or assigned tasker can cancel this task")

    previous_status = task.status
    fee = Decimal("0.00")
    refund_amount: Decimal | None = None
    refund_status: str | None = None

    if previous_status in _ACTIVE_STATUSES:
        open_dispute = (
            await db.execute(
                select(Dispute.id).where(Dispute.task_id == task.id, Dispute.status == DisputeStatus.OPEN).limit(1)
            )
        ).scalar_one_or_none()
        escrow = (await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))).scalar_one_or_none()
        if escrow is not None and escrow.status == EscrowStatus.RELEASED:
            raise MarketplaceError("conflict", "Payment was already released, so this task cannot be cancelled")
        if actor != CancelledBy.ADMIN and (
            open_dispute is not None or (escrow is not None and escrow.status in _ESCROW_BLOCKS_CANCEL)
        ):
            raise MarketplaceError("conflict", "Work is verified or disputed. Use the dispute flow instead.")

        if actor != CancelledBy.ADMIN:
            if escrow is not None and escrow.task_price is not None:
                price = escrow.task_price
            else:
                price = await agreed_task_price(db, task)
            fee = cancellation_fee(price)

        if escrow is not None:
            if actor == CancelledBy.POSTER:
                refund_amount = max(escrow.amount - fee, Decimal("0.00"))
            else:
                refund_amount = escrow.amount
            had_refund = bool(escrow.razorpay_refund_id)
            escrow.status = EscrowStatus.CANCELLED
            db.add(
                EscrowEvent(
                    escrow_payment_id=escrow.id,
                    type=EscrowEventType.CANCELLED,
                    metadata_json={
                        "source": "task_cancel",
                        "cancelled_by": actor.value,
                        "cancellation_fee": str(fee),
                        "refund_amount": str(refund_amount),
                    },
                )
            )
            if refund_amount <= 0:
                refund_status = "none"
            else:
                partial = refund_amount if refund_amount < escrow.amount else None
                try:
                    issued = await try_refund_escrow_capture(db, escrow, partial_amount_inr=partial)
                except httpx.HTTPStatusError as e:
                    await db.rollback()
                    raise MarketplaceError("refund_failed", f"Refund failed: {e.response.text[:300]}") from e
                if issued:
                    refund_status = "refunded"
                elif had_refund:
                    refund_status = "already_refunded"
                elif not escrow.razorpay_payment_id:
                    refund_status = "not_captured"
                else:
                    refund_status = "pending_manual"

        if actor == CancelledBy.TASKER and acceptance is not None:
            # Counts toward the repeated-cancellations trust heuristic.
            acceptance.status = AcceptanceStatus.CANCELLED

    pending_offers = (
        await db.execute(
            select(TaskOffer).where(TaskOffer.task_id == task.id, TaskOffer.status == OfferStatus.PENDING)
        )
    ).scalars().all()
    for offer in pending_offers:
        offer.status = OfferStatus.DECLINED

    task.status = TaskStatus.CANCELLED
    cancellation = TaskCancellation(
        task_id=task.id,
        cancelled_by_id=user.id,
        cancelled_by=actor,
        reason=reason,
        previous_status=previous_status.value,
        fee_amount=fee,
        refund_amount=refund_amount,
        refund_status=refund_status,
    )
    db.add(cancellation)
    await db.commit()
    await db.refresh(cancellation)

    notify_ids: set[uuid.UUID] = {o.tasker_id for o in pending_offers}
    if actor != CancelledBy.POSTER:
        notify_ids.add(task.poster_id)
    if acceptance is not None and actor != CancelledBy.TASKER:
        notify_ids.add(acceptance.tasker_id)
    for uid in notify_ids:
        await create_notification(
            db,
            user_id=uid,
            title="Task cancelled",
            body=f"The {task.category} task was cancelled by the {actor.value.lower()}.",
            category=NotificationCategory.TASK,
            payload={"task_id": str(task.id), "event": "task_cancelled", "cancelled_by": actor.value},
        )
    return cancellation

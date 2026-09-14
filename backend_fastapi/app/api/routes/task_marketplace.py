import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.db.session import get_db
from app.models.task import Task
from app.models.task_offer import OfferStatus, TaskCancellation, TaskOffer
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.schemas.task_marketplace import (
    CancelTaskRequest,
    CancelTaskResponse,
    FeeBreakdownResponse,
    OfferAcceptResponse,
    OfferCreateRequest,
    OfferResponse,
)
from app.services.audit_service import write_audit
from app.services.fee_service import compute_fees
from app.services.rating_service import get_user_rating_summary
from app.services.task_marketplace_service import (
    MarketplaceError,
    accept_offer,
    cancel_task,
    submit_offer,
    withdraw_offer,
)

router = APIRouter(prefix="/api/tasks", tags=["task-marketplace"])

_ERROR_STATUS = {
    "not_found": status.HTTP_404_NOT_FOUND,
    "forbidden": status.HTTP_403_FORBIDDEN,
    "conflict": status.HTTP_409_CONFLICT,
    "bad_request": status.HTTP_400_BAD_REQUEST,
    "refund_failed": status.HTTP_502_BAD_GATEWAY,
}


def _http_error(e: MarketplaceError) -> HTTPException:
    return HTTPException(status_code=_ERROR_STATUS.get(e.code, status.HTTP_400_BAD_REQUEST), detail=str(e))


def _parse_uuid(value: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {name}")


async def _offer_to_response(db: AsyncSession, offer: TaskOffer) -> OfferResponse:
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == offer.tasker_id))
    ).scalar_one_or_none()
    rating_average, rating_count = await get_user_rating_summary(db, offer.tasker_id)
    return OfferResponse(
        offer_id=str(offer.id),
        task_id=str(offer.task_id),
        tasker_id=str(offer.tasker_id),
        amount=str(offer.amount),
        currency=offer.currency,
        message=offer.message,
        status=offer.status.value,
        created_at=offer.created_at.isoformat(),
        updated_at=offer.updated_at.isoformat(),
        tasker_display_name=profile.display_name if profile else None,
        tasker_rating_average=rating_average,
        tasker_rating_count=rating_count,
        fees=FeeBreakdownResponse(**compute_fees(offer.amount).as_dict()),
    )


def _cancellation_to_response(c: TaskCancellation) -> CancelTaskResponse:
    return CancelTaskResponse(
        task_id=str(c.task_id),
        status="CANCELLED",
        cancelled_by=c.cancelled_by.value,
        previous_status=c.previous_status,
        reason=c.reason,
        fee_amount=str(c.fee_amount),
        refund_amount=str(c.refund_amount) if c.refund_amount is not None else None,
        refund_status=c.refund_status,
        created_at=c.created_at.isoformat(),
    )


@router.get("/fees/quote", response_model=FeeBreakdownResponse)
async def quote_fees(
    price: float = Query(gt=0, le=1_000_000),
    current_user: User = Depends(get_current_user),
):
    """Fee breakdown for a task price, shown before making or accepting an offer."""
    return FeeBreakdownResponse(**compute_fees(Decimal(str(price))).as_dict())


@router.post("/{task_id}/offers", response_model=OfferResponse)
async def make_offer(
    request: Request,
    task_id: str,
    payload: OfferCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Make an offer on a published task, or update your pending offer."""
    task_uuid = _parse_uuid(task_id, "task_id")
    amount = Decimal(str(round(payload.amount, 2)))
    message = payload.message.strip() if payload.message and payload.message.strip() else None
    try:
        offer, created = await submit_offer(db, task_uuid, current_user, amount=amount, message=message)
    except MarketplaceError as e:
        raise _http_error(e) from e

    await write_audit(
        db,
        user_id=current_user.id,
        action="offer_submit" if created else "offer_update",
        resource_type="task_offer",
        resource_id=offer.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task_uuid), "amount": str(offer.amount)},
    )
    return await _offer_to_response(db, offer)


@router.get("/{task_id}/offers", response_model=list[OfferResponse])
async def list_offers(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poster and staff see every offer; anyone else sees only their own."""
    task_uuid = _parse_uuid(task_id, "task_id")
    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    query = select(TaskOffer).where(TaskOffer.task_id == task.id)
    is_staff = current_user.role in {UserRole.ADMIN, UserRole.REVIEWER}
    if task.poster_id != current_user.id and not is_staff:
        query = query.where(TaskOffer.tasker_id == current_user.id)
    else:
        # Posters don't need to see offers taskers pulled back.
        query = query.where(TaskOffer.status != OfferStatus.WITHDRAWN)
    offers = (await db.execute(query.order_by(TaskOffer.amount.asc(), TaskOffer.created_at.asc()))).scalars().all()
    return [await _offer_to_response(db, o) for o in offers]


@router.post("/{task_id}/offers/{offer_id}/accept", response_model=OfferAcceptResponse)
async def accept_task_offer(
    request: Request,
    task_id: str,
    offer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poster assigns the task to this offer's tasker at the offered price."""
    task_uuid = _parse_uuid(task_id, "task_id")
    offer_uuid = _parse_uuid(offer_id, "offer_id")
    try:
        task, offer, acceptance = await accept_offer(db, task_uuid, offer_uuid, current_user)
    except MarketplaceError as e:
        raise _http_error(e) from e

    await write_audit(
        db,
        user_id=current_user.id,
        action="offer_accept",
        resource_type="task_offer",
        resource_id=offer.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id), "tasker_id": str(offer.tasker_id), "acceptance_id": str(acceptance.id)},
    )
    return OfferAcceptResponse(
        task_id=str(task.id),
        task_status=task.status.value,
        offer=await _offer_to_response(db, offer),
    )


@router.post("/{task_id}/offers/{offer_id}/withdraw", response_model=OfferResponse)
async def withdraw_task_offer(
    task_id: str,
    offer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_uuid = _parse_uuid(task_id, "task_id")
    offer_uuid = _parse_uuid(offer_id, "offer_id")
    try:
        offer = await withdraw_offer(db, task_uuid, offer_uuid, current_user)
    except MarketplaceError as e:
        raise _http_error(e) from e
    return await _offer_to_response(db, offer)


@router.post("/{task_id}/cancel", response_model=CancelTaskResponse)
async def cancel_task_route(
    request: Request,
    task_id: str,
    payload: CancelTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_uuid = _parse_uuid(task_id, "task_id")
    reason = payload.reason.strip() if payload.reason and payload.reason.strip() else None
    try:
        cancellation = await cancel_task(db, task_uuid, current_user, reason=reason)
    except MarketplaceError as e:
        raise _http_error(e) from e

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_cancel",
        resource_type="task",
        resource_id=task_uuid,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={
            "cancelled_by": cancellation.cancelled_by.value,
            "fee_amount": str(cancellation.fee_amount),
            "refund_status": cancellation.refund_status,
        },
    )
    return _cancellation_to_response(cancellation)

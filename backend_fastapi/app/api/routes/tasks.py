import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.db.session import get_db
from app.models.task import (
    Dispute,
    DisputeEvent,
    DisputeStatus,
    EscrowEvent,
    EscrowEventType,
    EscrowPayment,
    EscrowStatus,
    EvidenceUpload,
    Task,
    TaskAcceptance,
    TaskStatus,
    VerificationResult,
    VerificationStatus,
)
from app.models.task_rating import TaskRating
from app.models.task_collaboration import TaskScope, TaskScopeStatus
from app.models.user_profile import UserProfile
from app.models.platform_security import NotificationCategory
from app.models.task_offer import OfferStatus, TaskCancellation, TaskOffer
from app.models.user import User, UserRole, is_marketplace_user
from app.core.config import settings
from app.services.audit_service import write_audit
from app.services.escrow_pricing import create_held_escrow
from app.services.fee_service import compute_fees
from app.services.notification_service import create_notification
from app.services.task_lifecycle_notifications import (
    on_dispute_opened,
    on_dispute_resolved,
    on_escrow_released,
    on_escrow_started,
    on_task_accepted,
    on_verification_recorded,
)
from app.services.escrow_razorpay_refund import try_refund_escrow_capture
from app.services.tasker_escrow_payout import try_escrow_payout_to_tasker
from app.services.rating_service import (
    get_existing_rating,
    mark_task_completed,
    resolve_ratee_for_poster,
    task_is_rateable,
)
from app.services.task_publish_service import PublishDraftError, publish_draft_to_task
from app.services.pin_geocode import geocode_india_pin
from app.services.pin_utils import normalize_india_pin
from app.services.gemini_vision_verification_service import resolve_verification
from app.schemas.ratings import TaskRateRequest, TaskRatingResponse
from app.schemas.task_collaboration import TaskDetailResponse, TaskScopeResponse
from app.schemas.task import (
    AcceptTaskRequest,
    AcceptTaskResponse,
    DisputeCreateRequest,
    DisputeCreateResponse,
    DisputeListItem,
    DisputeResolveRequest,
    DisputeResolveResponse,
    VerificationReviewItem,
    EscrowReleaseResponse,
    EscrowStartResponse,
    EvidenceUploadRequest,
    EvidenceUploadResponse,
    EvidenceDetailResponse,
    PublishTaskResponse,
    TaskFeedItem,
    VerificationResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _rating_to_response(rating: TaskRating) -> TaskRatingResponse:
    return TaskRatingResponse(
        rating_id=str(rating.id),
        task_id=str(rating.task_id),
        rater_id=str(rating.rater_id),
        ratee_id=str(rating.ratee_id),
        score=rating.score,
        comment=rating.comment,
        created_at=rating.created_at.isoformat(),
    )


@router.post("/{draft_id}/publish", response_model=PublishTaskResponse)
async def publish_task(
    request: Request,
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid draft_id")

    try:
        task = await publish_draft_to_task(db, current_user, draft_uuid)
    except PublishDraftError as e:
        code = e.code
        if code == "not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        if code == "forbidden":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if code == "conflict":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_publish",
        resource_type="task",
        resource_id=task.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"draft_id": str(draft_uuid)},
    )
    await create_notification(
        db,
        user_id=current_user.id,
        title="Task published",
        body=f"Your task is live. task_id={task.id}",
        category=NotificationCategory.TASK,
        payload={"task_id": str(task.id), "category": task.category},
    )

    return PublishTaskResponse(
        id=str(task.id),
        poster_id=str(task.poster_id),
        status=task.status.value,
        category=task.category,
        subcategory=task.subcategory,
        task_schema=task.task_schema,
    )


def _task_to_feed_item(task: Task, *, my_relation: str | None = None) -> TaskFeedItem:
    coords = geocode_india_pin((task.task_schema or {}).get("location"))
    return TaskFeedItem(
        id=str(task.id),
        poster_id=str(task.poster_id),
        status=task.status.value,
        category=task.category,
        subcategory=task.subcategory,
        task_schema=task.task_schema,
        my_relation=my_relation,
        latitude=coords[0] if coords else None,
        longitude=coords[1] if coords else None,
    )


def _scope_to_response(scope: TaskScope) -> TaskScopeResponse:
    return TaskScopeResponse(
        scope_id=str(scope.id),
        task_id=str(scope.task_id),
        status=scope.status.value,
        agreed_price=str(scope.agreed_price),
        currency=scope.currency,
        scope_json=scope.scope_json,
        note=scope.note,
        proposed_by_id=str(scope.proposed_by_id),
        proposed_at=scope.proposed_at.isoformat(),
        agreed_at=scope.agreed_at.isoformat() if scope.agreed_at else None,
    )


async def _task_to_detail(db: AsyncSession, task: Task, viewer: User) -> TaskDetailResponse:
    acceptance = (
        await db.execute(
            select(TaskAcceptance)
            .where(TaskAcceptance.task_id == task.id)
            .order_by(TaskAcceptance.accepted_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    offers = (await db.execute(select(TaskOffer).where(TaskOffer.task_id == task.id))).scalars().all()
    my_offer = next((o for o in offers if o.tasker_id == viewer.id), None)
    cancellation = (
        await db.execute(select(TaskCancellation).where(TaskCancellation.task_id == task.id))
    ).scalar_one_or_none()

    scope_row = (
        await db.execute(select(TaskScope).where(TaskScope.task_id == task.id))
    ).scalar_one_or_none()

    escrow = (
        await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))
    ).scalar_one_or_none()

    evidence = (
        await db.execute(select(EvidenceUpload).where(EvidenceUpload.task_id == task.id).limit(1))
    ).scalar_one_or_none()

    verification = (
        await db.execute(
            select(VerificationResult)
            .where(VerificationResult.task_id == task.id)
            .order_by(VerificationResult.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return TaskDetailResponse(
        id=str(task.id),
        poster_id=str(task.poster_id),
        tasker_id=str(acceptance.tasker_id) if acceptance else None,
        status=task.status.value,
        category=task.category,
        subcategory=task.subcategory,
        task_schema=task.task_schema,
        scope=_scope_to_response(scope_row) if scope_row else None,
        escrow_status=escrow.status.value if escrow else None,
        escrow_amount=str(escrow.amount) if escrow else None,
        has_evidence=evidence is not None,
        verification_status=verification.status.value if verification else None,
        offer_count=sum(1 for o in offers if o.status in {OfferStatus.PENDING, OfferStatus.ACCEPTED}),
        my_offer_id=str(my_offer.id) if my_offer else None,
        my_offer_status=my_offer.status.value if my_offer else None,
        my_offer_amount=str(my_offer.amount) if my_offer else None,
        fees=compute_fees(scope_row.agreed_price).as_dict()
        if scope_row and scope_row.status == TaskScopeStatus.ACCEPTED
        else None,
        cancelled_by=cancellation.cancelled_by.value if cancellation else None,
        cancellation_reason=cancellation.reason if cancellation else None,
        cancellation_fee=str(cancellation.fee_amount) if cancellation else None,
    )


async def _get_task_or_404(db: AsyncSession, task_id: str) -> Task:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")
    result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _user_can_view_task(db: AsyncSession, task: Task, user: User) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.REVIEWER}:
        return True
    if task.poster_id == user.id:
        return True
    acceptance = await db.execute(
        select(TaskAcceptance).where(
            TaskAcceptance.task_id == task.id,
            TaskAcceptance.tasker_id == user.id,
        )
    )
    if acceptance.scalar_one_or_none() is not None:
        return True
    offer = await db.execute(
        select(TaskOffer.id).where(TaskOffer.task_id == task.id, TaskOffer.tasker_id == user.id)
    )
    return offer.scalar_one_or_none() is not None


@router.get("/mine", response_model=list[TaskFeedItem])
async def my_tasks(
    view: str = Query(default="all", pattern="^(all|posted|working)$"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tasks you posted and tasks you are working on or have offered on (one account does both)."""
    items: list[tuple[object, TaskFeedItem]] = []
    if view in {"all", "posted"}:
        posted = (
            await db.execute(
                select(Task).where(Task.poster_id == current_user.id).order_by(Task.created_at.desc()).limit(limit)
            )
        ).scalars().all()
        items.extend((t.created_at, _task_to_feed_item(t, my_relation="poster")) for t in posted)
    if view in {"all", "working"}:
        assigned = (
            await db.execute(
                select(Task, TaskAcceptance.accepted_at)
                .join(TaskAcceptance, TaskAcceptance.task_id == Task.id)
                .where(TaskAcceptance.tasker_id == current_user.id)
                .order_by(TaskAcceptance.accepted_at.desc())
                .limit(limit)
            )
        ).all()
        seen = {t.id for t, _ in assigned}
        items.extend((at, _task_to_feed_item(t, my_relation="tasker")) for t, at in assigned)
        offered = (
            await db.execute(
                select(Task, TaskOffer.updated_at)
                .join(TaskOffer, TaskOffer.task_id == Task.id)
                .where(TaskOffer.tasker_id == current_user.id, TaskOffer.status == OfferStatus.PENDING)
                .order_by(TaskOffer.updated_at.desc())
                .limit(limit)
            )
        ).all()
        items.extend((ut, _task_to_feed_item(t, my_relation="offer")) for t, ut in offered if t.id not in seen)
    items.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in items[:limit]]


@router.get("/feed", response_model=list[TaskFeedItem])
async def tasks_feed(
    category: str | None = Query(default=None),
    pin: str | None = Query(default=None, max_length=10),
    location_type: str | None = Query(default=None, pattern="^(IN_PERSON|REMOTE)$"),
    q: str | None = Query(default=None, max_length=200, description="Search task title/description"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_price must not exceed max_price")
    pin_norm: str | None = None
    if pin:
        try:
            pin_norm = normalize_india_pin(pin)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    query = select(Task).where(Task.status == TaskStatus.PUBLISHED)
    if current_user.role == UserRole.POSTER:
        query = query.where(Task.poster_id == current_user.id)
    if current_user.role == UserRole.TASKER:
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
        ).scalar_one_or_none()
        service_pins = list(profile.service_pin_codes or []) if profile else []
        query = query.where(Task.poster_id != current_user.id)
        # Remote tasks aren't bound by service PINs, so they show up regardless of area —
        # even for a tasker who hasn't set any PINs yet.
        is_remote = Task.task_schema["locationType"].astext == "REMOTE"
        if service_pins:
            pin_clauses = [Task.task_schema["location"].astext.like(f"%{p}%") for p in service_pins]
            query = query.where(or_(is_remote, *pin_clauses))
        else:
            query = query.where(is_remote)
        if pin_norm:
            if pin_norm not in service_pins:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="PIN not in your service areas — update profile",
                )
    if category:
        query = query.where(Task.category == category)
    if pin_norm:
        query = query.where(Task.task_schema["location"].astext.like(f"%{pin_norm}%"))
    if location_type:
        query = query.where(Task.task_schema["locationType"].astext == location_type)
    if q:
        needle = f"%{q.strip()}%"
        query = query.where(
            or_(
                Task.task_schema["title"].astext.ilike(needle),
                Task.task_schema["description"].astext.ilike(needle),
                Task.category.ilike(needle),
                Task.subcategory.ilike(needle),
            )
        )
    if min_price is not None:
        # NULL suggested_price_max means we don't know the ceiling, so don't exclude it on a floor filter.
        query = query.where(or_(Task.suggested_price_max.is_(None), Task.suggested_price_max >= min_price))
    if max_price is not None:
        query = query.where(or_(Task.suggested_price_min.is_(None), Task.suggested_price_min <= max_price))
    query = query.order_by(Task.created_at.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [_task_to_feed_item(task) for task in rows]


@router.get("/disputes/open", response_model=list[DisputeListItem])
async def list_open_disputes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or reviewer only")

    rows = (
        await db.execute(
            select(Dispute)
            .where(Dispute.status == DisputeStatus.OPEN)
            .order_by(Dispute.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        DisputeListItem(
            dispute_id=str(d.id),
            task_id=str(d.task_id),
            opened_by_id=str(d.opened_by_id),
            status=d.status.value,
            reason=d.reason,
            created_at=d.created_at.isoformat(),
        )
        for d in rows
    ]


@router.get("/admin/verifications/review", response_model=list[VerificationReviewItem])
async def list_verifications_for_review(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or reviewer only")

    rows = (
        await db.execute(
            select(VerificationResult)
            .where(VerificationResult.status != VerificationStatus.PASS)
            .order_by(VerificationResult.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        VerificationReviewItem(
            verification_id=str(v.id),
            task_id=str(v.task_id),
            status=v.status.value,
            confidence=v.confidence,
            explanation=v.explanation,
            created_at=v.created_at.isoformat(),
        )
        for v in rows
    ]


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    # Open tasks are browsable by any marketplace account so they can make an offer.
    if task.status == TaskStatus.PUBLISHED and is_marketplace_user(current_user):
        return await _task_to_detail(db, task, current_user)
    if not await _user_can_view_task(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this task")
    return await _task_to_detail(db, task, current_user)


@router.get("/{task_id}/evidence", response_model=EvidenceDetailResponse | None)
async def get_task_evidence(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if not await _user_can_view_task(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this task")

    evidence_result = await db.execute(
        select(EvidenceUpload)
        .where(EvidenceUpload.task_id == task.id)
        .order_by(EvidenceUpload.created_at.desc())
        .limit(1)
    )
    evidence = evidence_result.scalar_one_or_none()
    if not evidence:
        return None

    return EvidenceDetailResponse(
        evidence_id=str(evidence.id),
        task_id=str(evidence.task_id),
        uploaded_by_id=str(evidence.uploaded_by_id),
        before_image_url=evidence.before_image_url,
        after_image_url=evidence.after_image_url,
        evidence_video_url=evidence.evidence_video_url,
        uploaded_at=evidence.created_at.isoformat() if evidence.created_at else None,
    )


@router.post("/{task_id}/accept", response_model=AcceptTaskResponse)
async def accept_task(
    request: Request,
    task_id: str,
    payload: AcceptTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    if not settings.task_instant_accept_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Instant accept is disabled. Make an offer instead (POST /api/tasks/{task_id}/offers).",
        )
    if not is_marketplace_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only taskers can accept tasks")
    if not payload.acknowledge_requirements:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requirements must be acknowledged")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != TaskStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is not available for acceptance")
    if task.poster_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot accept your own task")

    existing = await db.execute(
        select(TaskAcceptance).where(
            TaskAcceptance.task_id == task.id,
            TaskAcceptance.tasker_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already accepted by this tasker")

    acceptance = TaskAcceptance(
        task_id=task.id,
        tasker_id=current_user.id,
        acknowledgement=payload.acknowledgement,
    )
    task.status = TaskStatus.ACCEPTED
    db.add(acceptance)
    await db.commit()
    await db.refresh(acceptance)

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_accept",
        resource_type="task",
        resource_id=task.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"acceptance_id": str(acceptance.id)},
    )
    await on_task_accepted(
        db,
        poster_id=task.poster_id,
        task_id=task.id,
        tasker_id=current_user.id,
        category=task.category,
    )

    return AcceptTaskResponse(
        acceptance_id=str(acceptance.id),
        task_id=str(acceptance.task_id),
        tasker_id=str(acceptance.tasker_id),
        status=acceptance.status.value,
    )


@router.post("/{task_id}/evidence", response_model=EvidenceUploadResponse)
async def upload_evidence(
    task_id: str,
    payload: EvidenceUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    acceptance_result = await db.execute(
        select(TaskAcceptance).where(TaskAcceptance.task_id == task.id, TaskAcceptance.tasker_id == current_user.id)
    )
    if not acceptance_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assigned tasker can upload evidence")

    evidence = EvidenceUpload(
        task_id=task.id,
        uploaded_by_id=current_user.id,
        before_image_url=payload.before_image_url,
        after_image_url=payload.after_image_url,
        evidence_video_url=payload.evidence_video_url,
        evidence_json=payload.evidence_json,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return EvidenceUploadResponse(
        evidence_id=str(evidence.id),
        task_id=str(evidence.task_id),
        uploaded_by_id=str(evidence.uploaded_by_id),
    )


@router.post("/{task_id}/verify", response_model=VerificationResponse)
async def verify_task_completion(
    request: Request,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.id != task.poster_id and current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only poster/admin can trigger verification")

    evidence_result = await db.execute(select(EvidenceUpload).where(EvidenceUpload.task_id == task.id))
    evidence = evidence_result.scalars().first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No evidence uploaded yet")

    status_value, confidence, explanation, _provider = resolve_verification(
        evidence, task_schema=task.task_schema
    )
    verification = VerificationResult(
        task_id=task.id,
        status=status_value,
        confidence=confidence,
        explanation=explanation,
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    escrow_result = await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))
    escrow = escrow_result.scalar_one_or_none()
    if escrow:
        if status_value == VerificationStatus.PASS:
            escrow.status = EscrowStatus.RELEASE_ELIGIBLE
            db.add(
                EscrowEvent(
                    escrow_payment_id=escrow.id,
                    type=EscrowEventType.RELEASE_ELIGIBLE,
                    metadata_json={"verification_id": str(verification.id)},
                )
            )
        else:
            escrow.status = EscrowStatus.DISPUTE_OPENED
            db.add(
                EscrowEvent(
                    escrow_payment_id=escrow.id,
                    type=EscrowEventType.DISPUTE_OPENED,
                    metadata_json={"verification_id": str(verification.id)},
                )
            )
        await db.commit()

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_verify",
        resource_type="task",
        resource_id=task.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"verification_id": str(verification.id), "status": verification.status.value},
    )
    await on_verification_recorded(
        db,
        task_id=task.id,
        poster_id=task.poster_id,
        status=verification.status.value,
        confidence=float(verification.confidence),
    )

    return VerificationResponse(
        verification_id=str(verification.id),
        task_id=str(verification.task_id),
        status=verification.status.value,
        confidence=verification.confidence,
        explanation=verification.explanation,
    )


@router.post("/{task_id}/escrow/start", response_model=EscrowStartResponse)
async def start_escrow(
    request: Request,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.id != task.poster_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only poster can start escrow")

    existing = await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))
    escrow = existing.scalar_one_or_none()
    if escrow:
        return EscrowStartResponse(
            escrow_payment_id=str(escrow.id),
            task_id=str(escrow.task_id),
            status=escrow.status.value,
            amount=str(escrow.amount),
            currency=escrow.currency,
            fees=_escrow_fees(escrow),
        )

    if task.status not in {TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Escrow can only be started once a tasker is assigned",
        )

    escrow = await create_held_escrow(db, task, source="mvp")
    await db.commit()
    await db.refresh(escrow)

    await write_audit(
        db,
        user_id=current_user.id,
        action="escrow_start",
        resource_type="escrow",
        resource_id=escrow.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id)},
    )
    await on_escrow_started(db, poster_id=task.poster_id, task_id=task.id)

    return EscrowStartResponse(
        escrow_payment_id=str(escrow.id),
        task_id=str(escrow.task_id),
        status=escrow.status.value,
        amount=str(escrow.amount),
        currency=escrow.currency,
        fees=_escrow_fees(escrow),
    )


def _escrow_fees(escrow: EscrowPayment) -> dict[str, str] | None:
    if escrow.task_price is None:
        return None
    return compute_fees(escrow.task_price).as_dict()


@router.get("/{task_id}/disputes", response_model=list[DisputeListItem])
async def list_task_disputes(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if not await _user_can_view_task(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this task")

    rows = (
        await db.execute(
            select(Dispute)
            .where(Dispute.task_id == task.id)
            .order_by(Dispute.created_at.desc())
        )
    ).scalars().all()
    return [
        DisputeListItem(
            dispute_id=str(d.id),
            task_id=str(d.task_id),
            opened_by_id=str(d.opened_by_id),
            status=d.status.value,
            reason=d.reason,
            created_at=d.created_at.isoformat(),
        )
        for d in rows
    ]


@router.post("/{task_id}/disputes", response_model=DisputeCreateResponse)
async def open_dispute(
    request: Request,
    task_id: str,
    payload: DisputeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    is_poster = current_user.id == task.poster_id
    is_tasker = bool(
        (
            await db.execute(
                select(TaskAcceptance).where(
                    TaskAcceptance.task_id == task.id,
                    TaskAcceptance.tasker_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
    )
    if not (is_poster or is_tasker or current_user.role in {UserRole.ADMIN, UserRole.REVIEWER}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to open dispute")

    dispute = Dispute(task_id=task.id, opened_by_id=current_user.id, status=DisputeStatus.OPEN, reason=payload.reason)
    db.add(dispute)
    await db.flush()
    db.add(DisputeEvent(dispute_id=dispute.id, type="OPENED", metadata_json={"reason": payload.reason}))

    escrow_result = await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))
    escrow = escrow_result.scalar_one_or_none()
    if escrow:
        escrow.status = EscrowStatus.DISPUTE_OPENED
        db.add(
            EscrowEvent(
                escrow_payment_id=escrow.id,
                type=EscrowEventType.DISPUTE_OPENED,
                metadata_json={"dispute_id": str(dispute.id)},
            )
        )

    await db.commit()

    await write_audit(
        db,
        user_id=current_user.id,
        action="dispute_open",
        resource_type="dispute",
        resource_id=dispute.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id)},
    )
    await on_dispute_opened(
        db,
        task_id=task.id,
        poster_id=task.poster_id,
        dispute_id=dispute.id,
        reason=payload.reason,
    )

    return DisputeCreateResponse(dispute_id=str(dispute.id), task_id=str(task.id), status=dispute.status.value)


@router.post("/{task_id}/escrow/release", response_model=EscrowReleaseResponse)
async def release_escrow(
    request: Request,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.id != task.poster_id and current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to release escrow")

    escrow_result = await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == task.id))
    escrow = escrow_result.scalar_one_or_none()
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")
    if escrow.status != EscrowStatus.RELEASE_ELIGIBLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Escrow cannot be released from status {escrow.status.value}",
        )

    escrow.status = EscrowStatus.RELEASED
    db.add(
        EscrowEvent(
            escrow_payment_id=escrow.id,
            type=EscrowEventType.RELEASED,
            metadata_json={"released_by": str(current_user.id)},
        )
    )
    await mark_task_completed(db, task)
    await db.commit()
    await db.refresh(escrow)
    payout_status = await try_escrow_payout_to_tasker(db, task, escrow)

    await write_audit(
        db,
        user_id=current_user.id,
        action="escrow_release",
        resource_type="escrow",
        resource_id=escrow.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id), "payout_status": payout_status},
    )
    await on_escrow_released(db, poster_id=task.poster_id, task_id=task.id)

    return EscrowReleaseResponse(
        escrow_payment_id=str(escrow.id),
        task_id=str(task.id),
        status=escrow.status.value,
        payout_status=payout_status,
    )


@router.post("/disputes/{dispute_id}/resolve", response_model=DisputeResolveResponse)
async def resolve_dispute(
    request: Request,
    dispute_id: str,
    payload: DisputeResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin/reviewer can resolve disputes")

    try:
        dispute_uuid = uuid.UUID(dispute_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dispute_id")

    dispute_result = await db.execute(select(Dispute).where(Dispute.id == dispute_uuid))
    dispute = dispute_result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    if dispute.status == DisputeStatus.RESOLVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dispute already resolved")

    task_row = await db.execute(select(Task).where(Task.id == dispute.task_id))
    task_for_dispute = task_row.scalar_one_or_none()
    if not task_for_dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    dispute.status = DisputeStatus.RESOLVED
    db.add(
        DisputeEvent(
            dispute_id=dispute.id,
            type="RESOLVED",
            metadata_json={"outcome": payload.outcome, "note": payload.note, "resolved_by": str(current_user.id)},
        )
    )

    escrow_status_value: str | None = None
    escrow_result = await db.execute(select(EscrowPayment).where(EscrowPayment.task_id == dispute.task_id))
    escrow = escrow_result.scalar_one_or_none()
    if escrow:
        if payload.outcome == "release":
            escrow.status = EscrowStatus.RELEASED
            db.add(
                EscrowEvent(
                    escrow_payment_id=escrow.id,
                    type=EscrowEventType.RELEASED,
                    metadata_json={"resolved_dispute_id": str(dispute.id)},
                )
            )
        else:
            escrow.status = EscrowStatus.CANCELLED
            db.add(
                EscrowEvent(
                    escrow_payment_id=escrow.id,
                    type=EscrowEventType.CANCELLED,
                    metadata_json={"resolved_dispute_id": str(dispute.id)},
                )
            )
        escrow_status_value = escrow.status.value

    if escrow and payload.outcome != "release":
        try:
            await try_refund_escrow_capture(db, escrow, dispute_id=dispute.id)
        except httpx.HTTPStatusError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Razorpay refund failed: {e.response.text[:300]}",
            ) from e

    if payload.outcome == "release":
        await mark_task_completed(db, task_for_dispute)

    await db.commit()

    if escrow and payload.outcome == "release":
        await db.refresh(escrow)
        await try_escrow_payout_to_tasker(db, task_for_dispute, escrow)

    await write_audit(
        db,
        user_id=current_user.id,
        action="dispute_resolve",
        resource_type="dispute",
        resource_id=dispute.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"outcome": payload.outcome, "task_id": str(dispute.task_id)},
    )
    await on_dispute_resolved(
        db,
        task_id=dispute.task_id,
        poster_id=task_for_dispute.poster_id,
        dispute_id=dispute.id,
        outcome=payload.outcome,
    )

    return DisputeResolveResponse(dispute_id=str(dispute.id), status=dispute.status.value, escrow_status=escrow_status_value)


@router.post("/{task_id}/rate", response_model=TaskRatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_task(
    request: Request,
    task_id: str,
    payload: TaskRateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not await task_is_rateable(db, task):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task can only be rated after escrow is released",
        )

    ratee_id = await resolve_ratee_for_poster(db, task, current_user.id)
    existing = await get_existing_rating(db, task_id=task.id, rater_id=current_user.id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already rated this task")

    comment = payload.comment.strip() if payload.comment else None
    rating = TaskRating(
        task_id=task.id,
        rater_id=current_user.id,
        ratee_id=ratee_id,
        score=payload.score,
        comment=comment,
    )
    db.add(rating)
    await db.commit()
    await db.refresh(rating)

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_rate",
        resource_type="task_rating",
        resource_id=rating.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id), "score": payload.score, "ratee_id": str(ratee_id)},
    )

    return _rating_to_response(rating)


@router.get("/{task_id}/rating", response_model=TaskRatingResponse | None)
async def get_my_task_rating(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")

    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    rating = await get_existing_rating(db, task_id=task.id, rater_id=current_user.id)
    if not rating:
        return None
    return _rating_to_response(rating)


import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
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
from app.models.platform_security import NotificationCategory
from app.models.user import User, UserRole
from app.services.audit_service import write_audit
from app.services.notification_service import create_notification
from app.services.task_lifecycle_notifications import (
    on_dispute_opened,
    on_dispute_resolved,
    on_escrow_released,
    on_escrow_started,
    on_task_accepted,
    on_verification_recorded,
)
from app.services.task_publish_service import PublishDraftError, publish_draft_to_task
from app.schemas.task import (
    AcceptTaskRequest,
    AcceptTaskResponse,
    DisputeCreateRequest,
    DisputeCreateResponse,
    DisputeResolveRequest,
    DisputeResolveResponse,
    EscrowReleaseResponse,
    EscrowStartResponse,
    EvidenceUploadRequest,
    EvidenceUploadResponse,
    PublishTaskResponse,
    TaskFeedItem,
    VerificationResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _mock_verification_status(evidence: EvidenceUpload) -> tuple[VerificationStatus, float, str]:
    has_before = bool(evidence.before_image_url)
    has_after = bool(evidence.after_image_url)
    has_video = bool(evidence.evidence_video_url)
    if has_before and has_after:
        return VerificationStatus.PASS, 0.92, "Before and after evidence available."
    if has_after or has_video:
        return VerificationStatus.LOW_CONFIDENCE, 0.62, "Partial evidence available; manual confirmation recommended."
    return VerificationStatus.FAIL, 0.18, "No sufficient completion evidence found."


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


@router.get("/feed", response_model=list[TaskFeedItem])
async def tasks_feed(
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Task).where(Task.status == TaskStatus.PUBLISHED)
    if current_user.role == UserRole.POSTER:
        query = query.where(Task.poster_id == current_user.id)
    if category:
        query = query.where(Task.category == category)
    query = query.order_by(Task.created_at.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        TaskFeedItem(
            id=str(task.id),
            poster_id=str(task.poster_id),
            status=task.status.value,
            category=task.category,
            subcategory=task.subcategory,
            task_schema=task.task_schema,
        )
        for task in rows
    ]


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

    if current_user.role != UserRole.TASKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only taskers can accept tasks")
    if not payload.acknowledge_requirements:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requirements must be acknowledged")

    task_result = await db.execute(select(Task).where(Task.id == task_uuid))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != TaskStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is not available for acceptance")

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

    status_value, confidence, explanation = _mock_verification_status(evidence)
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
        )

    amount = task.suggested_price_max or task.suggested_price_min or Decimal("1000.00")
    escrow = EscrowPayment(task_id=task.id, status=EscrowStatus.HELD, amount=amount, currency="INR")
    db.add(escrow)
    await db.flush()
    db.add(EscrowEvent(escrow_payment_id=escrow.id, type=EscrowEventType.HELD, metadata_json={"source": "mvp"}))
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
    )


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
    await db.commit()

    await write_audit(
        db,
        user_id=current_user.id,
        action="escrow_release",
        resource_type="escrow",
        resource_id=escrow.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id)},
    )
    await on_escrow_released(db, poster_id=task.poster_id, task_id=task.id)

    return EscrowReleaseResponse(escrow_payment_id=str(escrow.id), task_id=str(task.id), status=escrow.status.value)


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

    await db.commit()

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


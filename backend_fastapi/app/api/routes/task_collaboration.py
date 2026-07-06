import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task import Task, TaskAcceptance, TaskStatus, AcceptanceStatus
from app.models.task_collaboration import TaskScope, TaskScopeStatus, TaskThreadMessage
from app.models.user_profile import UserProfile
from app.models.user import User, UserRole
from app.schemas.task_collaboration import (
    TaskScopeProposeRequest,
    TaskScopeResponse,
    TaskThreadMessageCreate,
    TaskThreadMessageResponse,
)
from app.services.task_translate_service import translate_for_task_thread

router = APIRouter(prefix="/api/tasks", tags=["task-collaboration"])


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


async def _get_acceptance(db: AsyncSession, task: Task) -> TaskAcceptance | None:
    result = await db.execute(
        select(TaskAcceptance).where(
            TaskAcceptance.task_id == task.id,
            TaskAcceptance.status == AcceptanceStatus.ACCEPTED,
        )
    )
    return result.scalar_one_or_none()


async def _participant_ids(db: AsyncSession, task: Task) -> tuple[uuid.UUID, uuid.UUID | None]:
    acceptance = await _get_acceptance(db, task)
    tasker_id = acceptance.tasker_id if acceptance else None
    return task.poster_id, tasker_id


async def _user_is_participant(db: AsyncSession, task: Task, user: User) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.REVIEWER}:
        return True
    poster_id, tasker_id = await _participant_ids(db, task)
    if user.id == poster_id:
        return True
    return tasker_id is not None and user.id == tasker_id


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


def _message_to_response(msg: TaskThreadMessage) -> TaskThreadMessageResponse:
    return TaskThreadMessageResponse(
        id=str(msg.id),
        task_id=str(msg.task_id),
        sender_id=str(msg.sender_id),
        original_text=msg.original_text,
        translated_text=msg.translated_text,
        source_lang=msg.source_lang,
        target_lang=msg.target_lang,
        translation_provider=msg.translation_provider,
        created_at=msg.created_at.isoformat(),
    )


@router.get("/{task_id}/scope", response_model=TaskScopeResponse | None)
async def get_task_scope(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if not await _user_is_participant(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = await db.execute(select(TaskScope).where(TaskScope.task_id == task.id))
    scope = result.scalar_one_or_none()
    return _scope_to_response(scope) if scope else None


@router.post("/{task_id}/scope/propose", response_model=TaskScopeResponse)
async def propose_task_scope(
    task_id: str,
    payload: TaskScopeProposeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if task.status not in {TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task must be accepted first")

    acceptance = await _get_acceptance(db, task)
    if not acceptance:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No tasker assigned")
    if current_user.id != acceptance.tasker_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned tasker can propose scope")

    existing = await db.execute(select(TaskScope).where(TaskScope.task_id == task.id))
    scope = existing.scalar_one_or_none()
    if scope and scope.status == TaskScopeStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scope already agreed")

    price = Decimal(str(round(payload.agreed_price, 2)))
    if scope:
        scope.agreed_price = price
        scope.currency = payload.currency
        scope.scope_json = payload.scope_json
        scope.note = payload.note
        scope.proposed_by_id = current_user.id
        scope.status = TaskScopeStatus.PROPOSED
        scope.agreed_at = None
    else:
        scope = TaskScope(
            task_id=task.id,
            poster_id=task.poster_id,
            tasker_id=acceptance.tasker_id,
            proposed_by_id=current_user.id,
            agreed_price=price,
            currency=payload.currency,
            scope_json=payload.scope_json,
            note=payload.note,
            status=TaskScopeStatus.PROPOSED,
        )
        db.add(scope)

    await db.commit()
    await db.refresh(scope)
    return _scope_to_response(scope)


@router.post("/{task_id}/scope/accept", response_model=TaskScopeResponse)
async def accept_task_scope(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if current_user.id != task.poster_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the poster can accept scope")

    result = await db.execute(select(TaskScope).where(TaskScope.task_id == task.id))
    scope = result.scalar_one_or_none()
    if not scope or scope.status != TaskScopeStatus.PROPOSED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending scope proposal")

    from datetime import datetime, timezone

    scope.status = TaskScopeStatus.ACCEPTED
    scope.agreed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(scope)
    return _scope_to_response(scope)


@router.get("/{task_id}/messages", response_model=list[TaskThreadMessageResponse])
async def list_task_messages(
    task_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if not await _user_is_participant(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    result = await db.execute(
        select(TaskThreadMessage)
        .where(TaskThreadMessage.task_id == task.id)
        .order_by(TaskThreadMessage.created_at.asc())
        .limit(min(limit, 100))
    )
    return [_message_to_response(m) for m in result.scalars().all()]


@router.post("/{task_id}/messages", response_model=TaskThreadMessageResponse, status_code=status.HTTP_201_CREATED)
async def post_task_message(
    task_id: str,
    payload: TaskThreadMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if task.status == TaskStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Accept the task before messaging")
    if not await _user_is_participant(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    poster_id, tasker_id = await _participant_ids(db, task)
    target = payload.target_lang
    if not target or target == "auto":
        if current_user.id == poster_id and tasker_id:
            prof = (
                await db.execute(select(UserProfile).where(UserProfile.user_id == tasker_id))
            ).scalar_one_or_none()
            target = (prof.preferred_languages[0] if prof and prof.preferred_languages else None) or "hi"
        else:
            prof = (
                await db.execute(select(UserProfile).where(UserProfile.user_id == poster_id))
            ).scalar_one_or_none()
            target = (prof.preferred_languages[0] if prof and prof.preferred_languages else None) or "en"

    translated, src_out, _detected, provider = await translate_for_task_thread(
        payload.text.strip(),
        payload.source_lang,
        target,
    )

    msg = TaskThreadMessage(
        task_id=task.id,
        sender_id=current_user.id,
        original_text=payload.text.strip(),
        translated_text=translated if translated != payload.text.strip() else None,
        source_lang=src_out,
        target_lang=target,
        translation_provider=provider,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return _message_to_response(msg)

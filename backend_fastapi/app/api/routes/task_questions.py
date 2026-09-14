import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.db.session import get_db
from app.models.platform_security import NotificationCategory
from app.models.task import Task, TaskStatus
from app.models.task_question import TaskQuestion
from app.models.user import User, is_marketplace_user
from app.models.user_profile import UserProfile
from app.schemas.task_question import TaskQuestionAnswerRequest, TaskQuestionCreateRequest, TaskQuestionResponse
from app.services.audit_service import write_audit
from app.services.notification_service import create_notification

router = APIRouter(prefix="/api/tasks", tags=["task-questions"])


async def _get_task_or_404(db: AsyncSession, task_id: str) -> Task:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")
    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _to_response(db: AsyncSession, q: TaskQuestion) -> TaskQuestionResponse:
    profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == q.asker_id))).scalar_one_or_none()
    return TaskQuestionResponse(
        id=str(q.id),
        task_id=str(q.task_id),
        asker_id=str(q.asker_id),
        asker_display_name=profile.display_name if profile else None,
        question=q.question,
        answer=q.answer,
        answered_at=q.answered_at.isoformat() if q.answered_at else None,
        created_at=q.created_at.isoformat(),
    )


@router.get("/{task_id}/questions", response_model=list[TaskQuestionResponse])
async def list_task_questions(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Public Q&A on the task — visible to any signed-in account, like Airtasker's open task page."""
    task = await _get_task_or_404(db, task_id)
    rows = (
        await db.execute(select(TaskQuestion).where(TaskQuestion.task_id == task.id).order_by(TaskQuestion.created_at.asc()))
    ).scalars().all()
    return [await _to_response(db, q) for q in rows]


@router.post("/{task_id}/questions", response_model=TaskQuestionResponse, status_code=status.HTTP_201_CREATED)
async def ask_task_question(
    request: Request,
    task_id: str,
    payload: TaskQuestionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if not is_marketplace_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only poster/tasker accounts can ask questions")
    if task.poster_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't ask a question on your own task")
    if task.status != TaskStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Questions are only open while the task is published")

    q = TaskQuestion(task_id=task.id, asker_id=current_user.id, question=payload.question.strip())
    db.add(q)
    await db.commit()
    await db.refresh(q)

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_question_ask",
        resource_type="task_question",
        resource_id=q.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id)},
    )
    await create_notification(
        db,
        user_id=task.poster_id,
        title="New question on your task",
        body=q.question[:200],
        category=NotificationCategory.TASK,
        payload={"task_id": str(task.id), "question_id": str(q.id), "event": "question_asked"},
    )
    return await _to_response(db, q)


@router.post("/{task_id}/questions/{question_id}/answer", response_model=TaskQuestionResponse)
async def answer_task_question(
    request: Request,
    task_id: str,
    question_id: str,
    payload: TaskQuestionAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await _get_task_or_404(db, task_id)
    if task.poster_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the poster can answer questions")

    try:
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid question_id")
    q = (
        await db.execute(select(TaskQuestion).where(TaskQuestion.id == question_uuid, TaskQuestion.task_id == task.id))
    ).scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    q.answer = payload.answer.strip()
    q.answered_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(q)

    await write_audit(
        db,
        user_id=current_user.id,
        action="task_question_answer",
        resource_type="task_question",
        resource_id=q.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"task_id": str(task.id)},
    )
    await create_notification(
        db,
        user_id=q.asker_id,
        title="Your question was answered",
        body=q.answer[:200],
        category=NotificationCategory.TASK,
        payload={"task_id": str(task.id), "question_id": str(q.id), "event": "question_answered"},
    )
    return await _to_response(db, q)

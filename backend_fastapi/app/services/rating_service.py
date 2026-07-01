import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import AcceptanceStatus, EscrowPayment, EscrowStatus, Task, TaskAcceptance, TaskStatus
from app.models.task_rating import TaskRating


async def get_accepted_tasker_id(db: AsyncSession, task_id: uuid.UUID) -> uuid.UUID | None:
    row = await db.execute(
        select(TaskAcceptance.tasker_id).where(
            TaskAcceptance.task_id == task_id,
            TaskAcceptance.status == AcceptanceStatus.ACCEPTED,
        )
    )
    return row.scalar_one_or_none()


async def task_is_rateable(db: AsyncSession, task: Task) -> bool:
    if task.status == TaskStatus.COMPLETED:
        return True
    escrow_row = await db.execute(select(EscrowPayment.status).where(EscrowPayment.task_id == task.id))
    escrow_status = escrow_row.scalar_one_or_none()
    return escrow_status == EscrowStatus.RELEASED


async def resolve_ratee_for_poster(db: AsyncSession, task: Task, rater_id: uuid.UUID) -> uuid.UUID:
    if rater_id != task.poster_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the task poster can rate the tasker after completion",
        )
    tasker_id = await get_accepted_tasker_id(db, task.id)
    if not tasker_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task has no accepted tasker")
    return tasker_id


async def get_user_rating_summary(db: AsyncSession, user_id: uuid.UUID) -> tuple[float | None, int]:
    row = await db.execute(
        select(func.avg(TaskRating.score), func.count(TaskRating.id)).where(TaskRating.ratee_id == user_id)
    )
    avg_score, count = row.one()
    if not count:
        return None, 0
    return round(float(avg_score), 2), int(count)


async def get_existing_rating(
    db: AsyncSession, *, task_id: uuid.UUID, rater_id: uuid.UUID
) -> TaskRating | None:
    row = await db.execute(
        select(TaskRating).where(TaskRating.task_id == task_id, TaskRating.rater_id == rater_id)
    )
    return row.scalar_one_or_none()


async def mark_task_completed(db: AsyncSession, task: Task) -> None:
    if task.status != TaskStatus.COMPLETED:
        task.status = TaskStatus.COMPLETED
        db.add(task)

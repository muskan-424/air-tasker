from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_security import NotificationCategory
from app.models.task import TaskAcceptance
from app.services.notification_service import create_notification


async def tasker_id_for_task(db: AsyncSession, task_id: uuid.UUID) -> uuid.UUID | None:
    row = (await db.execute(select(TaskAcceptance).where(TaskAcceptance.task_id == task_id))).scalar_one_or_none()
    return row.tasker_id if row else None


async def on_task_accepted(
    db: AsyncSession, *, poster_id: uuid.UUID, task_id: uuid.UUID, tasker_id: uuid.UUID, category: str
) -> None:
    await create_notification(
        db,
        user_id=poster_id,
        title="Task accepted",
        body=f"A tasker accepted your task ({category}). task_id={task_id}",
        category=NotificationCategory.TASK,
        payload={"task_id": str(task_id), "tasker_id": str(tasker_id), "event": "accepted"},
    )


async def on_escrow_started(db: AsyncSession, *, poster_id: uuid.UUID, task_id: uuid.UUID) -> None:
    tid = await tasker_id_for_task(db, task_id)
    if not tid:
        return
    await create_notification(
        db,
        user_id=tid,
        title="Escrow started",
        body=f"Poster started escrow for task {task_id}.",
        category=NotificationCategory.ESCROW,
        payload={"task_id": str(task_id), "poster_id": str(poster_id), "event": "escrow_started"},
    )


async def on_escrow_released(db: AsyncSession, *, poster_id: uuid.UUID, task_id: uuid.UUID) -> None:
    tid = await tasker_id_for_task(db, task_id)
    if not tid:
        return
    await create_notification(
        db,
        user_id=tid,
        title="Escrow released",
        body=f"Escrow was released for task {task_id}.",
        category=NotificationCategory.ESCROW,
        payload={"task_id": str(task_id), "event": "escrow_released"},
    )


async def on_dispute_opened(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    poster_id: uuid.UUID,
    dispute_id: uuid.UUID,
    reason: str,
) -> None:
    tid = await tasker_id_for_task(db, task_id)
    snippet = (reason or "")[:200]
    body = f"A dispute was opened on task {task_id}."
    payload = {"task_id": str(task_id), "dispute_id": str(dispute_id), "reason": snippet}
    targets: list[uuid.UUID] = [poster_id]
    if tid:
        targets.append(tid)
    for uid in targets:
        await create_notification(
            db,
            user_id=uid,
            title="Dispute opened",
            body=body,
            category=NotificationCategory.DISPUTE,
            payload=payload,
        )


async def on_dispute_resolved(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    poster_id: uuid.UUID,
    dispute_id: uuid.UUID,
    outcome: str,
) -> None:
    tid = await tasker_id_for_task(db, task_id)
    body = f"Dispute {dispute_id} resolved with outcome: {outcome}. task_id={task_id}"
    targets: list[uuid.UUID] = [poster_id]
    if tid:
        targets.append(tid)
    for uid in targets:
        await create_notification(
            db,
            user_id=uid,
            title="Dispute resolved",
            body=body,
            category=NotificationCategory.DISPUTE,
            payload={"task_id": str(task_id), "dispute_id": str(dispute_id), "outcome": outcome},
        )


async def on_verification_recorded(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    poster_id: uuid.UUID,
    status: str,
    confidence: float,
) -> None:
    tid = await tasker_id_for_task(db, task_id)
    if tid:
        await create_notification(
            db,
            user_id=tid,
            title="Verification update",
            body=f"Verification for task {task_id}: {status} (confidence {confidence:.2f}).",
            category=NotificationCategory.TASK,
            payload={"task_id": str(task_id), "status": status, "event": "verification"},
        )
    await create_notification(
        db,
        user_id=poster_id,
        title="Verification update",
        body=f"Verification for task {task_id}: {status}.",
        category=NotificationCategory.TASK,
        payload={"task_id": str(task_id), "status": status, "event": "verification"},
    )

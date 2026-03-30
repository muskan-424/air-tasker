from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.task_draft import TaskDraft
from app.models.user import User


class PublishDraftError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _extract_price_range(ai_schema: dict) -> tuple[Decimal | None, Decimal | None]:
    price = ai_schema.get("suggestedPriceRange") if isinstance(ai_schema, dict) else None
    if not isinstance(price, dict):
        return None, None
    min_val = price.get("min")
    max_val = price.get("max")
    try:
        min_decimal = Decimal(str(min_val)) if min_val is not None else None
        max_decimal = Decimal(str(max_val)) if max_val is not None else None
        return min_decimal, max_decimal
    except Exception:
        return None, None


async def publish_draft_to_task(db: AsyncSession, user: User, draft_id: uuid.UUID) -> Task:
    """Create a published Task from a draft; same rules as POST /api/tasks/{draft_id}/publish."""
    draft = (await db.execute(select(TaskDraft).where(TaskDraft.id == draft_id))).scalar_one_or_none()
    if not draft:
        raise PublishDraftError("not_found", "Draft not found")
    if draft.poster_id != user.id:
        raise PublishDraftError("forbidden", "Not allowed to publish this draft")
    existing_task = (await db.execute(select(Task).where(Task.draft_id == draft.id))).scalar_one_or_none()
    if existing_task:
        raise PublishDraftError("conflict", "Draft already published")

    ai_schema = draft.user_edits or draft.ai_schema
    category = str(ai_schema.get("category", "general"))
    subcategory = ai_schema.get("subcategory")
    min_price, max_price = _extract_price_range(ai_schema)

    task = Task(
        poster_id=user.id,
        draft_id=draft.id,
        status=TaskStatus.PUBLISHED,
        category=category,
        subcategory=subcategory,
        task_schema=ai_schema,
        suggested_price_min=min_price,
        suggested_price_max=max_price,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

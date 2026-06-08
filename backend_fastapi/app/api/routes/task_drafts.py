import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task_draft import TaskDraft
from app.models.user import User
from app.schemas.task_draft import TaskDraftCreateRequest, TaskDraftResponse, TaskDraftUpdateRequest
from app.services.task_chat_schema_service import build_ai_schema_from_message

router = APIRouter(prefix="/api/tasks/drafts", tags=["task-drafts"])


def _draft_to_response(draft: TaskDraft) -> TaskDraftResponse:
    effective_schema = draft.user_edits or draft.ai_schema
    return TaskDraftResponse(
        id=str(draft.id),
        poster_id=str(draft.poster_id),
        status=draft.status.value,
        ai_schema=effective_schema,
        ai_explain=draft.ai_explain,
    )


@router.get("/{draft_id}", response_model=TaskDraftResponse)
async def get_task_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid draft_id")

    draft = (await db.execute(select(TaskDraft).where(TaskDraft.id == draft_uuid))).scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.poster_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this draft")

    return _draft_to_response(draft)


@router.patch("/{draft_id}", response_model=TaskDraftResponse)
async def update_task_draft(
    draft_id: str,
    payload: TaskDraftUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        draft_uuid = uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid draft_id")

    draft = (await db.execute(select(TaskDraft).where(TaskDraft.id == draft_uuid))).scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.poster_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to edit this draft")

    draft.user_edits = payload.ai_schema
    await db.commit()
    await db.refresh(draft)

    return _draft_to_response(draft)


@router.post("", response_model=TaskDraftResponse)
async def create_task_draft(
    payload: TaskDraftCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ai_schema = build_ai_schema_from_message(payload.raw_input)
    if payload.language:
        ai_schema["language"] = payload.language
    draft = TaskDraft(
        poster_id=current_user.id,
        ai_schema=ai_schema,
        ai_explain="Structured draft from rule-based parser (shared with chat). Refine via Gemini later.",
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return _draft_to_response(draft)


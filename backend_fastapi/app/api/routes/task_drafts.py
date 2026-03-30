from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.task_draft import TaskDraft
from app.models.user import User
from app.schemas.task_draft import TaskDraftCreateRequest, TaskDraftResponse
from app.services.task_chat_schema_service import build_ai_schema_from_message

router = APIRouter(prefix="/api/tasks/drafts", tags=["task-drafts"])


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

    return TaskDraftResponse(
        id=str(draft.id),
        poster_id=str(draft.poster_id),
        status=draft.status.value,
        ai_schema=draft.ai_schema,
        ai_explain=draft.ai_explain,
    )


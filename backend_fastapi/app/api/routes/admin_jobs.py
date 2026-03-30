from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin_user
from app.models.user import User
from app.workers.job_queue import enqueue

router = APIRouter(prefix="/api/admin/jobs", tags=["admin-jobs"])


class EnqueueBody(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)


@router.post("/enqueue")
async def enqueue_job(
    body: EnqueueBody,
    _admin: User = Depends(get_current_admin_user),
):
    _ = _admin
    await enqueue(body.kind, body.payload)
    return {"status": "queued"}

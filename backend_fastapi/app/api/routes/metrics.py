from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin_user
from app.models.user import User
from app.services.metrics_service import snapshot

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/internal/summary")
async def metrics_summary(_admin: User = Depends(get_current_admin_user)):
    return {"counters": snapshot()}

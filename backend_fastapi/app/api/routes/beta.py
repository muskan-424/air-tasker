from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_current_user_optional
from app.db.session import get_db
from app.models.beta_feedback import BetaFeedback, BetaFeedbackCategory
from app.models.user import User
from app.schemas.beta import (
    BetaConfigResponse,
    BetaFeedbackRequest,
    BetaFeedbackResponse,
    BetaKpiResponse,
)
from app.services.beta_kpi_service import beta_kpi_snapshot
from app.services.beta_service import beta_config_payload

router = APIRouter(prefix="/api/beta", tags=["beta"])


@router.get("/config", response_model=BetaConfigResponse)
async def get_beta_config():
    return beta_config_payload()


@router.post("/feedback", response_model=BetaFeedbackResponse)
async def submit_beta_feedback(
    payload: BetaFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    row = BetaFeedback(
        user_id=current_user.id if current_user else None,
        email=payload.email or (current_user.email if current_user else None),
        category=BetaFeedbackCategory(payload.category),
        message=payload.message.strip(),
        page_path=payload.page_path,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return BetaFeedbackResponse(feedback_id=str(row.id))


@router.get("/kpis", response_model=BetaKpiResponse)
async def get_beta_kpis(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    _ = _admin
    return await beta_kpi_snapshot(db)

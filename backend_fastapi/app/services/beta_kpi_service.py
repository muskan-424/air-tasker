from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.beta_feedback import BetaFeedback
from app.models.task import Dispute, DisputeStatus, EscrowPayment, Task, TaskAcceptance, TaskStatus
from app.models.task_draft import TaskDraft
from app.services.beta_service import beta_categories, beta_pin_codes
from app.services.metrics_service import snapshot


async def beta_kpi_snapshot(db: AsyncSession) -> dict:
    published = int(
        (await db.execute(select(func.count()).select_from(Task).where(Task.status != TaskStatus.CANCELLED)))
        .scalar_one()
    )
    completed = int(
        (await db.execute(select(func.count()).select_from(Task).where(Task.status == TaskStatus.COMPLETED)))
        .scalar_one()
    )
    accepted = int(
        (await db.execute(select(func.count(func.distinct(TaskAcceptance.task_id))))).scalar_one()
    )
    escrow_tasks = int((await db.execute(select(func.count()).select_from(EscrowPayment))).scalar_one())
    open_disputes = int(
        (
            await db.execute(
                select(func.count()).select_from(Dispute).where(Dispute.status == DisputeStatus.OPEN)
            )
        ).scalar_one()
    )
    draft_count = int((await db.execute(select(func.count()).select_from(TaskDraft))).scalar_one())

    median_publish = (
        await db.execute(
            select(
                func.percentile_cont(0.5).within_group(
                    func.extract("epoch", Task.created_at - TaskDraft.created_at)
                )
            )
            .select_from(Task)
            .join(TaskDraft, TaskDraft.id == Task.draft_id)
        )
    ).scalar_one()

    counters = snapshot()
    gemini_calls = counters.get("gemini_calls_total", 0)
    ai_calls_estimated = gemini_calls + draft_count
    cost_per_call = float(settings.beta_gemini_cost_inr_per_call)

    accept_rate = round(accepted / published, 4) if published else 0.0
    dispute_rate = round(open_disputes / escrow_tasks, 4) if escrow_tasks else 0.0

    return {
        "window": "all_time",
        "published_tasks": published,
        "completed_tasks": completed,
        "accepted_tasks": accepted,
        "accept_rate": accept_rate,
        "open_disputes": open_disputes,
        "escrow_tasks": escrow_tasks,
        "dispute_rate": dispute_rate,
        "median_time_to_publish_seconds": float(median_publish) if median_publish is not None else None,
        "draft_count": draft_count,
        "ai_calls_estimated": ai_calls_estimated,
        "ai_cost_inr_estimated": round(ai_calls_estimated * cost_per_call, 2),
        "beta_categories": beta_categories(),
        "beta_pin_codes": beta_pin_codes(),
    }

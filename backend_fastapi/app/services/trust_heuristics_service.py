from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.models.task import AcceptanceStatus, Task, TaskAcceptance, TaskStatus, VerificationResult, VerificationStatus
from app.models.trust_report import TrustFlag, TrustFlagSeverity, TrustFlagStatus, UserReport
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def _active_flag_exists(db: AsyncSession, user_id: uuid.UUID, rule_code: str) -> bool:
    row = (
        await db.execute(
            select(TrustFlag.id).where(
                TrustFlag.user_id == user_id,
                TrustFlag.rule_code == rule_code,
                TrustFlag.status == TrustFlagStatus.ACTIVE.value,
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def _upsert_flag(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    rule_code: str,
    severity: str,
    details: dict,
    source_report_id: uuid.UUID | None = None,
) -> TrustFlag | None:
    if await _active_flag_exists(db, user_id, rule_code):
        return None
    flag = TrustFlag(
        user_id=user_id,
        rule_code=rule_code,
        severity=severity,
        details=details,
        source_report_id=source_report_id,
        status=TrustFlagStatus.ACTIVE.value,
    )
    db.add(flag)
    return flag


async def evaluate_user_trust(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    cfg: Settings | None = None,
    source_report_id: uuid.UUID | None = None,
) -> list[TrustFlag]:
    cfg = cfg or settings
    now = _utcnow()
    flags: list[TrustFlag] = []

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        return flags

    cancel_since = now - timedelta(days=cfg.trust_cancel_window_days)
    cancel_count = (
        await db.execute(
            select(func.count(TaskAcceptance.id)).where(
                TaskAcceptance.tasker_id == user_id,
                TaskAcceptance.status == AcceptanceStatus.CANCELLED,
                TaskAcceptance.accepted_at >= cancel_since,
            )
        )
    ).scalar_one()
    if cancel_count >= cfg.trust_cancel_threshold:
        f = await _upsert_flag(
            db,
            user_id=user_id,
            rule_code="repeated_cancellations",
            severity=TrustFlagSeverity.MEDIUM.value,
            details={"count": int(cancel_count), "window_days": cfg.trust_cancel_window_days},
            source_report_id=source_report_id,
        )
        if f:
            flags.append(f)

    evidence_since = now - timedelta(days=cfg.trust_evidence_fail_window_days)
    fail_count = (
        await db.execute(
            select(func.count(VerificationResult.id))
            .join(Task, Task.id == VerificationResult.task_id)
            .where(
                Task.poster_id == user_id,
                VerificationResult.status.in_([VerificationStatus.FAIL, VerificationStatus.LOW_CONFIDENCE]),
                VerificationResult.created_at >= evidence_since,
            )
        )
    ).scalar_one()
    if fail_count >= cfg.trust_evidence_fail_threshold:
        f = await _upsert_flag(
            db,
            user_id=user_id,
            rule_code="evidence_mismatch_pattern",
            severity=TrustFlagSeverity.HIGH.value,
            details={"count": int(fail_count), "window_days": cfg.trust_evidence_fail_window_days},
            source_report_id=source_report_id,
        )
        if f:
            flags.append(f)

    created = user.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    account_age_days = (now - created).days
    if account_age_days <= cfg.trust_new_account_days:
        day_start = now - timedelta(days=1)
        recent_tasks = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.poster_id == user_id,
                    Task.created_at >= day_start,
                    Task.status != TaskStatus.CANCELLED,
                )
            )
        ).scalar_one()
        if recent_tasks >= cfg.trust_new_account_max_tasks_per_day:
            f = await _upsert_flag(
                db,
                user_id=user_id,
                rule_code="new_account_velocity",
                severity=TrustFlagSeverity.MEDIUM.value,
                details={
                    "tasks_last_24h": int(recent_tasks),
                    "account_age_days": account_age_days,
                    "limit": cfg.trust_new_account_max_tasks_per_day,
                },
                source_report_id=source_report_id,
            )
            if f:
                flags.append(f)

    return flags


async def evaluate_report_targets(
    db: AsyncSession,
    report: UserReport,
) -> list[TrustFlag]:
    flags: list[TrustFlag] = []
    if report.reported_user_id:
        flags.extend(
            await evaluate_user_trust(db, report.reported_user_id, source_report_id=report.id)
        )
    return flags

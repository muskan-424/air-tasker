import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.db.session import get_db
from app.models.task import Task
from app.models.trust_report import ReportStatus, TrustFlag, TrustFlagStatus, UserReport
from app.models.user import User, UserRole
from app.schemas.reports import (
    ReportCreateRequest,
    ReportCreateResponse,
    ReportListItem,
    ReportResolveRequest,
    TrustFlagItem,
)
from app.services.audit_service import write_audit
from app.services.trust_heuristics_service import evaluate_report_targets

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _require_reviewer(user: User) -> None:
    if user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or reviewer only")


@router.post("", response_model=ReportCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: Request,
    payload: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.reported_user_id and not payload.task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide reported_user_id and/or task_id",
        )

    reported_uuid: uuid.UUID | None = None
    task_uuid: uuid.UUID | None = None

    if payload.reported_user_id:
        try:
            reported_uuid = uuid.UUID(payload.reported_user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reported_user_id")
        if reported_uuid == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot report yourself")

    if payload.task_id:
        try:
            task_uuid = uuid.UUID(payload.task_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_id")
        task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if not reported_uuid:
            reported_uuid = task.poster_id if current_user.id != task.poster_id else None

    report = UserReport(
        reporter_id=current_user.id,
        reported_user_id=reported_uuid,
        task_id=task_uuid,
        category=payload.category,
        reason=payload.reason.strip(),
        status=ReportStatus.OPEN.value,
    )
    db.add(report)
    await db.flush()

    new_flags = await evaluate_report_targets(db, report)
    await db.commit()
    await db.refresh(report)

    await write_audit(
        db,
        user_id=current_user.id,
        action="user_report_create",
        resource_type="user_report",
        resource_id=report.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"category": payload.category, "task_id": str(task_uuid) if task_uuid else None},
    )

    return ReportCreateResponse(
        report_id=str(report.id),
        status=report.status,
        trust_flags_raised=[f.rule_code for f in new_flags],
    )


@router.get("/open", response_model=list[ReportListItem])
async def list_open_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reviewer(current_user)
    rows = (
        await db.execute(
            select(UserReport)
            .where(UserReport.status == ReportStatus.OPEN.value)
            .order_by(UserReport.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        ReportListItem(
            report_id=str(r.id),
            reporter_id=str(r.reporter_id),
            reported_user_id=str(r.reported_user_id) if r.reported_user_id else None,
            task_id=str(r.task_id) if r.task_id else None,
            category=r.category,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/{report_id}/resolve", response_model=ReportListItem)
async def resolve_report(
    report_id: str,
    payload: ReportResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reviewer(current_user)
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report_id")

    report = (await db.execute(select(UserReport).where(UserReport.id == rid))).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.status = ReportStatus.REVIEWED.value if payload.outcome == "reviewed" else ReportStatus.DISMISSED.value
    report.admin_notes = payload.admin_notes
    report.reviewed_by_id = current_user.id
    report.reviewed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(report)

    return ReportListItem(
        report_id=str(report.id),
        reporter_id=str(report.reporter_id),
        reported_user_id=str(report.reported_user_id) if report.reported_user_id else None,
        task_id=str(report.task_id) if report.task_id else None,
        category=report.category,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at.isoformat(),
    )


@router.get("/trust-flags/active", response_model=list[TrustFlagItem])
async def list_active_trust_flags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reviewer(current_user)
    rows = (
        await db.execute(
            select(TrustFlag)
            .where(TrustFlag.status == TrustFlagStatus.ACTIVE.value)
            .order_by(TrustFlag.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        TrustFlagItem(
            flag_id=str(f.id),
            user_id=str(f.user_id),
            rule_code=f.rule_code,
            severity=f.severity,
            status=f.status,
            details=f.details,
            created_at=f.created_at.isoformat(),
        )
        for f in rows
    ]

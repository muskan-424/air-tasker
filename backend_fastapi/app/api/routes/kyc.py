import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.kyc import KycStatus, UserKycProfile
from app.models.user import User, UserRole
from app.schemas.kyc import KycAdminReviewRequest, KycStatusResponse, KycSubmitRequest
from app.services.audit_service import write_audit
from app.services.kyc_service import admin_review_kyc, get_kyc_profile, submit_kyc

router = APIRouter(prefix="/api/kyc", tags=["kyc"])


def _serialize_profile(p: UserKycProfile, *, include_user_id: bool = False) -> KycStatusResponse:
    return KycStatusResponse(
        status=p.status.value,
        user_id=str(p.user_id) if include_user_id else None,
        provider=p.provider,
        full_name=p.full_name,
        pan_masked=f"XXXX{p.pan_last4}",
        aadhaar_last4=p.aadhaar_last4,
        submitted_at=p.submitted_at.isoformat() if p.submitted_at else None,
        verified_at=p.verified_at.isoformat() if p.verified_at else None,
        rejected_at=p.rejected_at.isoformat() if p.rejected_at else None,
        rejection_reason=p.rejection_reason,
    )


@router.get("/me", response_model=KycStatusResponse)
async def get_my_kyc(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await get_kyc_profile(db, current_user.id)
    if not profile:
        return KycStatusResponse(status="none")
    return _serialize_profile(profile)


@router.post("/submit", response_model=KycStatusResponse)
@limiter.limit("10/minute")
async def submit_kyc(
    request: Request,
    body: KycSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        profile = await submit_kyc(
            db,
            user=current_user,
            full_name=body.full_name,
            pan=body.pan,
            aadhaar_last4=body.aadhaar_last4,
        )
    except ValueError as e:
        code = str(e)
        if code == "already_verified":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="KYC already verified") from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from e

    await write_audit(
        db,
        user_id=current_user.id,
        action="kyc_submit",
        resource_type="kyc",
        resource_id=profile.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"status": profile.status.value, "provider": profile.provider},
    )
    return _serialize_profile(profile)


@router.post("/admin/{user_id}/review", response_model=KycStatusResponse)
async def admin_review_user_kyc(
    request: Request,
    user_id: str,
    body: KycAdminReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or reviewer only")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")

    profile = await get_kyc_profile(db, uid)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No KYC profile for user")

    if profile.status != KycStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="KYC is not pending review",
        )

    approve = body.decision == "approve"
    if not approve and not (body.reason and body.reason.strip()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reason required for rejection")

    profile = await admin_review_kyc(db, profile=profile, approve=approve, reason=body.reason)

    await write_audit(
        db,
        user_id=current_user.id,
        action="kyc_admin_review",
        resource_type="kyc",
        resource_id=profile.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta={"subject_user_id": str(uid), "decision": body.decision},
    )
    return _serialize_profile(profile)


@router.get("/admin/pending", response_model=list[KycStatusResponse])
async def list_pending_kyc(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or reviewer only")

    rows = (
        await db.execute(select(UserKycProfile).where(UserKycProfile.status == KycStatus.PENDING))
    ).scalars().all()
    return [_serialize_profile(p, include_user_id=True) for p in rows]

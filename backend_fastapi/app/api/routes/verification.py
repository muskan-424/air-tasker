from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, get_user_agent
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.platform_security import OtpPurpose, UserTrustedDevice
from app.models.user import User
from app.schemas.verification import OtpRequestBody, OtpVerifyBody, TrustedDeviceRegister
from app.services.audit_service import write_audit
from app.services.otp_service import create_and_send_otp, verify_otp

router = APIRouter(prefix="/api/verification", tags=["verification"])


@router.post("/email/request-otp")
@limiter.limit("15/minute")
async def request_email_otp(
    request: Request,
    payload: OtpRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.purpose == OtpPurpose.EMAIL_VERIFICATION and current_user.email_verified_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")

    await create_and_send_otp(
        db,
        email=current_user.email,
        user_id=current_user.id,
        purpose=payload.purpose,
    )
    await write_audit(
        db,
        user_id=current_user.id,
        action="otp_request",
        resource_type="otp",
        meta={"purpose": payload.purpose.value},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"status": "sent", "ttl_seconds": settings.otp_ttl_seconds}


@router.post("/email/verify")
@limiter.limit("15/minute")
async def verify_email_otp(
    request: Request,
    payload: OtpVerifyBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await verify_otp(
        db,
        email=current_user.email,
        user_id=current_user.id,
        purpose=payload.purpose,
        code=payload.code,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")

    if payload.purpose == OtpPurpose.EMAIL_VERIFICATION:
        current_user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()

    await write_audit(
        db,
        user_id=current_user.id,
        action="otp_verified",
        resource_type="otp",
        meta={"purpose": payload.purpose.value},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"status": "verified"}


@router.post("/devices/register")
async def register_trusted_device(
    request: Request,
    payload: TrustedDeviceRegister,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = UserTrustedDevice(
        user_id=current_user.id,
        fingerprint=payload.fingerprint,
        label=payload.label,
    )
    db.add(row)
    await db.commit()
    await write_audit(
        db,
        user_id=current_user.id,
        action="trusted_device_register",
        meta={"fingerprint": payload.fingerprint[:16]},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"status": "ok", "device_id": str(row.id)}

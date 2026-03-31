from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kyc import KycStatus, UserKycProfile
from app.models.user import User
from app.services.kyc_providers.factory import get_kyc_provider
from app.services.metrics_service import inc


async def get_kyc_profile(db: AsyncSession, user_id: uuid.UUID) -> UserKycProfile | None:
    row = await db.execute(select(UserKycProfile).where(UserKycProfile.user_id == user_id))
    return row.scalar_one_or_none()


async def user_has_verified_kyc(db: AsyncSession, user_id: uuid.UUID) -> bool:
    profile = await get_kyc_profile(db, user_id)
    return profile is not None and profile.status == KycStatus.VERIFIED


async def submit_kyc(
    db: AsyncSession,
    *,
    user: User,
    full_name: str,
    pan: str,
    aadhaar_last4: str | None,
) -> UserKycProfile:
    existing = await get_kyc_profile(db, user.id)
    if existing and existing.status == KycStatus.VERIFIED:
        raise ValueError("already_verified")

    last4 = pan[5:9]
    now = datetime.now(timezone.utc)
    provider = get_kyc_provider()

    if existing:
        profile = existing
        profile.full_name = full_name
        profile.pan_last4 = last4
        profile.aadhaar_last4 = aadhaar_last4
        profile.submitted_at = now
        profile.rejection_reason = None
        profile.rejected_at = None
        profile.verified_at = None
    else:
        profile = UserKycProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            status=KycStatus.PENDING,
            provider=provider.name,
            full_name=full_name,
            pan_last4=last4,
            aadhaar_last4=aadhaar_last4,
            submitted_at=now,
        )

    provider.assign_reference_and_status(profile, now=now)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    inc("kyc_submissions_total")
    return profile


async def admin_review_kyc(
    db: AsyncSession,
    *,
    profile: UserKycProfile,
    approve: bool,
    reason: str | None,
) -> UserKycProfile:
    now = datetime.now(timezone.utc)
    if approve:
        profile.status = KycStatus.VERIFIED
        profile.verified_at = now
        profile.rejected_at = None
        profile.rejection_reason = None
        inc("kyc_verified_total")
    else:
        profile.status = KycStatus.REJECTED
        profile.rejected_at = now
        profile.rejection_reason = (reason or "").strip()[:500] or None
        profile.verified_at = None
        inc("kyc_rejected_total")

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

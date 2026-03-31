from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kyc import KycStatus, UserKycProfile


async def kyc_snapshot(db: AsyncSession) -> dict[str, object]:
    total = int((await db.execute(select(func.count()).select_from(UserKycProfile))).scalar_one() or 0)
    pending = int(
        (
            await db.execute(
                select(func.count()).select_from(UserKycProfile).where(UserKycProfile.status == KycStatus.PENDING)
            )
        ).scalar_one()
        or 0
    )
    verified = int(
        (
            await db.execute(
                select(func.count()).select_from(UserKycProfile).where(UserKycProfile.status == KycStatus.VERIFIED)
            )
        ).scalar_one()
        or 0
    )
    rejected = int(
        (
            await db.execute(
                select(func.count()).select_from(UserKycProfile).where(UserKycProfile.status == KycStatus.REJECTED)
            )
        ).scalar_one()
        or 0
    )
    return {
        "kyc_profiles_total": total,
        "kyc_status_pending": pending,
        "kyc_status_verified": verified,
        "kyc_status_rejected": rejected,
    }

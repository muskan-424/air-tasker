from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.models.kyc import KycStatus, UserKycProfile
from app.services.kyc_providers.base import KycProvider
from app.services.metrics_service import inc


class StubKycProvider(KycProvider):
    name = "stub"

    def assign_reference_and_status(self, profile: UserKycProfile, *, now: datetime) -> None:
        profile.provider = self.name
        profile.provider_reference_id = f"stub_{profile.id}".replace("-", "")[:40]

        if settings.kyc_stub_auto_verify:
            profile.status = KycStatus.VERIFIED
            profile.verified_at = now
            inc("kyc_verified_total")
        else:
            profile.status = KycStatus.PENDING


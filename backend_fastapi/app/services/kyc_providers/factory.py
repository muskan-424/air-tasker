from __future__ import annotations

from app.core.config import settings
from app.services.kyc_providers.base import KycProvider
from app.services.kyc_providers.stub_provider import StubKycProvider


def get_kyc_provider() -> KycProvider:
    key = (settings.kyc_provider or "stub").strip().lower()
    if key in ("stub", "", "mock"):
        return StubKycProvider()
    # Future: signzy, digilocker — default to stub until implemented
    return StubKycProvider()

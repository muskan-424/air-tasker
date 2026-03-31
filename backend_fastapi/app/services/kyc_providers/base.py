from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.kyc import UserKycProfile


class KycProvider(ABC):
    """Pluggable KYC backend (stub now; Signzy / DigiLocker adapters later)."""

    name: str

    @abstractmethod
    def assign_reference_and_status(
        self,
        profile: "UserKycProfile",
        *,
        now: datetime,
    ) -> None:
        """Set `provider_reference_id`, `status`, `verified_at` on the in-memory profile before DB flush."""


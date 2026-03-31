"""
Inbound webhooks from external KYC vendors (Signzy, etc.).

Body shape (MVP): {"provider_reference_id": "...", "status": "verified"|"rejected", "reason": "..."}
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kyc import KycStatus, UserKycProfile
from app.services.metrics_service import inc

logger = logging.getLogger(__name__)


def verify_kyc_webhook_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def apply_kyc_provider_webhook(
    db: AsyncSession,
    payload: dict[str, Any],
) -> dict[str, str]:
    ref = (payload.get("provider_reference_id") or payload.get("reference_id") or "").strip()
    if not ref:
        return {"result": "ignored", "reason": "missing provider_reference_id"}

    raw = (payload.get("status") or "").strip().lower()
    if raw not in ("verified", "rejected", "failed"):
        return {"result": "ignored", "reason": "unsupported status"}

    row = await db.execute(select(UserKycProfile).where(UserKycProfile.provider_reference_id == ref))
    profile = row.scalar_one_or_none()
    if not profile:
        logger.info("KYC webhook: no profile for reference_id=%s", ref[:20])
        return {"result": "ok", "note": "no matching profile"}

    now = datetime.now(timezone.utc)
    reason = (payload.get("reason") or payload.get("rejection_reason") or "").strip()[:500] or None

    if raw in ("verified",):
        profile.status = KycStatus.VERIFIED
        profile.verified_at = now
        profile.rejected_at = None
        profile.rejection_reason = None
        inc("kyc_verified_total")
    else:
        profile.status = KycStatus.REJECTED
        profile.rejected_at = now
        profile.rejection_reason = reason
        profile.verified_at = None
        inc("kyc_rejected_total")

    meta = dict(profile.metadata_json or {})
    meta["last_webhook"] = {"status": raw, "at": now.isoformat()}
    profile.metadata_json = meta
    db.add(profile)
    await db.commit()
    return {"result": "ok", "user_id": str(profile.user_id)}

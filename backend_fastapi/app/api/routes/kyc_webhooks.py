import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.kyc_webhook_service import apply_kyc_provider_webhook, verify_kyc_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/kyc", tags=["webhooks-kyc"])


@router.post("")
async def kyc_provider_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Vendor callback when async KYC completes. Send raw JSON body; optional `X-KYC-Signature` HMAC-SHA256(hex)
    when `KYC_WEBHOOK_SECRET` is set.
    """
    body = await request.body()
    sig = request.headers.get("X-KYC-Signature")

    if settings.kyc_webhook_secret:
        if not verify_kyc_webhook_signature(body, sig, settings.kyc_webhook_secret):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    else:
        if settings.environment.lower() not in {"development", "dev", "test"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="KYC webhook secret is required outside development/test",
            )
        logger.warning("KYC_WEBHOOK_SECRET not set; accepting KYC webhook without signature verification")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON object required")

    out = await apply_kyc_provider_webhook(db, payload)
    return {"status": "ok", **out}

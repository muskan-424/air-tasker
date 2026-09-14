from __future__ import annotations

import logging

from app.core.config import settings
from app.services.phone_utils import to_e164_india

logger = logging.getLogger(__name__)


async def send_sms(phone_10_digit: str, body: str) -> str:
    """Send SMS via the configured gateway, or log a stub when none is configured.

    No India SMS gateway (e.g. MSG91, Twilio) is wired up yet — this is a seam for one.
    Until `sms_gateway_url` is set, codes are logged instead of delivered.
    """
    to = to_e164_india(phone_10_digit)
    if not settings.sms_gateway_url:
        logger.info("[sms stub] to=%s\n%s", to, body)
        return "stub"

    # Real gateway not implemented yet; treat a configured URL as intent-to-integrate.
    logger.warning("SMS_GATEWAY_URL is set but no gateway integration exists yet; falling back to stub for %s", to)
    return "stub"

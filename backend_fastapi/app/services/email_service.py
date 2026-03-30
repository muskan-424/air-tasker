from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> str:
    """Send email or log stub when SMTP is not configured."""
    if not settings.smtp_host:
        logger.info("[email stub] to=%s subject=%s\n%s", to, subject, body)
        return "stub"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from or settings.smtp_user or "noreply@localhost"
    msg["To"] = to
    msg.set_content(body)

    def _send_sync() -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_user and settings.smtp_password:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

    import asyncio

    await asyncio.to_thread(_send_sync)
    return "sent"

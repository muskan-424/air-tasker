from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.platform_security import OtpChallenge, OtpChannel, OtpPurpose
from app.services.email_service import send_email
from app.services.sms_service import send_sms


def _hash_code(code: str) -> str:
    return hashlib.sha256(f"{settings.secret_key}:{code}".encode()).hexdigest()


def _generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))


async def create_and_send_otp(
    db: AsyncSession,
    *,
    target: str,
    user_id,
    purpose: OtpPurpose,
    channel: OtpChannel = OtpChannel.EMAIL,
) -> str:
    code = _generate_code()
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.otp_ttl_seconds)
    normalized = target.lower().strip() if channel == OtpChannel.EMAIL else target.strip()
    row = OtpChallenge(
        target=normalized,
        channel=channel.value,
        user_id=user_id,
        purpose=purpose.value,
        code_hash=_hash_code(code),
        expires_at=expires,
    )
    db.add(row)
    await db.commit()

    minutes = settings.otp_ttl_seconds // 60
    if channel == OtpChannel.SMS:
        body = f"Your VayuTask verification code is {code}. It expires in {minutes} minutes."
        delivery = await send_sms(normalized, body)
    else:
        subj = "Your VayuTask verification code"
        if purpose == OtpPurpose.EMAIL_VERIFICATION:
            body = (
                f"Your email verification code is: {code}\n"
                f"It expires in {minutes} minutes.\n\n"
                "Enter this code on the Account page in the app."
            )
        else:
            body = f"Your security code is: {code}\nIt expires in {minutes} minutes."
        delivery = await send_email(normalized, subj, body)
    return delivery


async def verify_otp(
    db: AsyncSession,
    *,
    target: str,
    user_id,
    purpose: OtpPurpose,
    code: str,
    channel: OtpChannel = OtpChannel.EMAIL,
) -> bool:
    normalized = target.lower().strip() if channel == OtpChannel.EMAIL else target.strip()
    q = (
        select(OtpChallenge)
        .where(
            OtpChallenge.target == normalized,
            OtpChallenge.channel == channel.value,
            OtpChallenge.purpose == purpose.value,
            OtpChallenge.consumed_at.is_(None),
        )
        .order_by(OtpChallenge.created_at.desc())
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        return False
    if row.user_id and user_id and row.user_id != user_id:
        return False
    if datetime.now(timezone.utc) > row.expires_at:
        return False
    if row.attempt_count >= settings.otp_max_attempts:
        return False
    row.attempt_count += 1
    if _hash_code(code.strip()) != row.code_hash:
        await db.commit()
        return False
    row.consumed_at = datetime.now(timezone.utc)
    await db.commit()
    return True

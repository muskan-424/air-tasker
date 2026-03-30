from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.platform_security import OtpChallenge, OtpPurpose
from app.services.email_service import send_email


def _hash_code(code: str) -> str:
    return hashlib.sha256(f"{settings.secret_key}:{code}".encode()).hexdigest()


def _generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))


async def create_and_send_otp(
    db: AsyncSession,
    *,
    email: str,
    user_id,
    purpose: OtpPurpose,
) -> None:
    code = _generate_code()
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.otp_ttl_seconds)
    row = OtpChallenge(
        email=email.lower().strip(),
        user_id=user_id,
        purpose=purpose.value,
        code_hash=_hash_code(code),
        expires_at=expires,
    )
    db.add(row)
    await db.commit()

    subj = "Your verification code"
    if purpose == OtpPurpose.EMAIL_VERIFICATION:
        body = f"Your email verification code is: {code}\nIt expires in {settings.otp_ttl_seconds // 60} minutes."
    else:
        body = f"Your security code is: {code}\nIt expires in {settings.otp_ttl_seconds // 60} minutes."

    await send_email(email, subj, body)


async def verify_otp(
    db: AsyncSession,
    *,
    email: str,
    user_id,
    purpose: OtpPurpose,
    code: str,
) -> bool:
    q = (
        select(OtpChallenge)
        .where(
            OtpChallenge.email == email.lower().strip(),
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

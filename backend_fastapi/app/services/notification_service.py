from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_security import Notification, NotificationCategory, NotificationPreference
from app.models.user import User
from app.services.email_service import send_email


async def get_or_create_prefs(db: AsyncSession, user_id: uuid.UUID) -> NotificationPreference:
    row = (await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))).scalar_one_or_none()
    if row:
        return row
    row = NotificationPreference(user_id=user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    body: str,
    category: NotificationCategory,
    payload: dict | None = None,
) -> Notification:
    prefs = await get_or_create_prefs(db, user_id)
    n = Notification(
        user_id=user_id,
        title=title,
        body=body,
        category=category.value,
        payload=payload,
        delivery_status="delivered",
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        return n

    want = False
    if category == NotificationCategory.TASK and prefs.email_task:
        want = True
    elif category == NotificationCategory.ESCROW and prefs.email_escrow:
        want = True
    elif category == NotificationCategory.DISPUTE and prefs.email_dispute:
        want = True
    elif category == NotificationCategory.SYSTEM:
        want = True

    if prefs.email_enabled and want:
        await send_email(user.email, title, body)

    return n

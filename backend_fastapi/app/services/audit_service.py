from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_security import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    meta: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(row)
    await db.commit()

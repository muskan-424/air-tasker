import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.platform_security import Notification
from app.models.user import User
from app.schemas.notifications import NotificationOut, NotificationPrefsOut, NotificationPrefsUpdate
from app.services.notification_realtime import notification_hub
from app.services.notification_service import get_or_create_prefs

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(min(limit, 100))
    )
    rows = (await db.execute(q)).scalars().all()
    return [
        NotificationOut(
            id=str(n.id),
            title=n.title,
            body=n.body,
            category=n.category,
            read_at=n.read_at.isoformat() if n.read_at else None,
            delivery_status=n.delivery_status,
            created_at=n.created_at.isoformat(),
        )
        for n in rows
    ]


@router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id")
    n = (
        await db.execute(select(Notification).where(Notification.id == nid, Notification.user_id == current_user.id))
    ).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    n.read_at = datetime.now(timezone.utc)
    await db.commit()
    return None


@router.get("/preferences", response_model=NotificationPrefsOut)
async def get_prefs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await get_or_create_prefs(db, current_user.id)
    return NotificationPrefsOut(
        in_app_enabled=p.in_app_enabled,
        email_enabled=p.email_enabled,
        email_task=p.email_task,
        email_escrow=p.email_escrow,
        email_dispute=p.email_dispute,
    )


@router.put("/preferences", response_model=NotificationPrefsOut)
async def put_prefs(
    payload: NotificationPrefsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await get_or_create_prefs(db, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    return NotificationPrefsOut(
        in_app_enabled=p.in_app_enabled,
        email_enabled=p.email_enabled,
        email_task=p.email_task,
        email_escrow=p.email_escrow,
        email_dispute=p.email_dispute,
    )


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="missing token")
        return
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_uuid = uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=1008, reason="invalid token")
        return

    await notification_hub.connect(user_uuid, websocket)
    try:
        while True:
            # Keep alive: accept ping and return pong.
            msg = await websocket.receive_text()
            if (msg or "").strip().lower() == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await notification_hub.disconnect(user_uuid, websocket)

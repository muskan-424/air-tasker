"""Fan out notification WebSocket events across processes via Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from app.core.config import settings
from app.services.metrics_service import inc
from app.services.notification_realtime import notification_hub

logger = logging.getLogger(__name__)

NOTIFICATION_CHANNEL = "airtasker:notifications"


async def broadcast_notification_event(user_id: uuid.UUID, event: dict) -> None:
    """Deliver to WebSockets: Redis pub/sub when REDIS_URL is set, else in-process hub only."""
    if settings.redis_url:
        try:
            import redis.asyncio as redis

            r = redis.from_url(settings.redis_url, decode_responses=True)
            try:
                await r.publish(
                    NOTIFICATION_CHANNEL,
                    json.dumps({"user_id": str(user_id), "event": event}),
                )
                inc("notifications_redis_published_total")
                return
            finally:
                await r.aclose()
        except Exception:
            logger.exception("Redis notification publish failed; falling back to local WebSocket fanout")

    await notification_hub.publish_to_user(user_id, event)


async def notification_redis_listener() -> None:
    """Subscribe to Redis and push to local WebSocket connections (one task per worker)."""
    if not settings.redis_url:
        return

    import redis.asyncio as redis

    r = redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(NOTIFICATION_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                data = json.loads(message["data"])
                uid = uuid.UUID(data["user_id"])
                event = data["event"]
                if isinstance(event, dict):
                    await notification_hub.publish_to_user(uid, event)
            except Exception:
                logger.exception("Failed to handle Redis notification message")
    except asyncio.CancelledError:
        raise
    finally:
        try:
            await pubsub.unsubscribe(NOTIFICATION_CHANNEL)
        except Exception:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass
        try:
            await r.aclose()
        except Exception:
            try:
                await r.close()
            except Exception:
                pass

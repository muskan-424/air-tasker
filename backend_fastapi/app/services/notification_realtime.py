from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict

from fastapi import WebSocket


class NotificationHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)

    async def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(user_id)
            if not conns:
                return
            conns.discard(websocket)
            if not conns:
                self._connections.pop(user_id, None)

    async def publish_to_user(self, user_id: uuid.UUID, event: dict) -> int:
        async with self._lock:
            targets = list(self._connections.get(user_id, set()))
        if not targets:
            return 0

        sent = 0
        payload = json.dumps(event, separators=(",", ":"))
        for ws in targets:
            try:
                await ws.send_text(payload)
                sent += 1
            except Exception:
                await self.disconnect(user_id, ws)
        return sent


notification_hub = NotificationHub()

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.core.config import settings

_mem: dict[str, tuple[float, str]] = {}
_lock = asyncio.Lock()


async def cache_get(key: str) -> Any | None:
    if settings.redis_url:
        try:
            import redis.asyncio as redis

            r = redis.from_url(settings.redis_url, decode_responses=True)
            raw = await r.get(key)
            await r.close()
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            pass
    async with _lock:
        entry = _mem.get(key)
        if not entry:
            return None
        exp, val = entry
        if exp < time.monotonic():
            del _mem[key]
            return None
        return json.loads(val)


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    payload = json.dumps(value).encode()
    if settings.redis_url:
        try:
            import redis.asyncio as redis

            r = redis.from_url(settings.redis_url, decode_responses=True)
            await r.set(key, payload.decode(), ex=ttl_seconds)
            await r.close()
            return
        except Exception:
            pass
    async with _lock:
        _mem[key] = (time.monotonic() + ttl_seconds, payload.decode())

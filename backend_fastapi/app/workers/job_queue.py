"""In-process async job queue (MVP). Replace with Redis/RQ/Celery for production."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()


async def enqueue(kind: str, payload: dict[str, Any]) -> None:
    await queue.put((kind, payload))


async def worker_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            kind, payload = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        try:
            logger.info("job processed kind=%s payload=%s", kind, payload)
        except Exception:
            logger.exception("job failed kind=%s", kind)


def start_worker(stop: asyncio.Event) -> asyncio.Task:
    return asyncio.create_task(worker_loop(stop))

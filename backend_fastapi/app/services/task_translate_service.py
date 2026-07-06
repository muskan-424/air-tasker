from __future__ import annotations

import asyncio

from app.core.config import settings
from app.services.translation_service import stub_translate, translate_sync


async def translate_for_task_thread(
    text: str,
    source_lang: str,
    target_lang: str,
) -> tuple[str, str, str | None, str]:
    """Translate message for poster↔tasker thread; falls back to stub."""
    if source_lang == target_lang:
        return text, source_lang, None, "none"
    try:
        return await asyncio.to_thread(translate_sync, text, source_lang, target_lang, settings)
    except Exception:
        translated, src_out, detected, provider = stub_translate(text, target_lang, source_lang)
        return translated, src_out, detected, provider

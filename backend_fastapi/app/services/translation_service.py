from __future__ import annotations

import json
import logging
import re

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


def _gemini_ok(cfg: Settings) -> bool:
    return bool(cfg.gemini_api_key and not cfg.use_mock_chatbot)


def translate_sync(
    text: str,
    source_lang: str,
    target_lang: str,
    app_settings: Settings | None = None,
) -> tuple[str, str, str | None, str]:
    """
    Returns (translated_text, source_lang_for_response, detected_source_or_none, provider).
    When source_lang is 'auto', uses JSON response with detection.
    """
    cfg = app_settings or settings
    if not _gemini_ok(cfg):
        raise RuntimeError("Gemini not configured")

    import google.generativeai as genai

    genai.configure(api_key=cfg.gemini_api_key)
    model_name = cfg.gemini_model_fast or cfg.gemini_model
    gcfg_kwargs: dict = {"temperature": 0.2, "max_output_tokens": 2048}
    if source_lang.lower() == "auto":
        gcfg_kwargs["response_mime_type"] = "application/json"
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(**gcfg_kwargs),
    )

    if source_lang.lower() == "auto":
        prompt = f"""Detect the language of the text and translate it into the target language.
Target language code: {target_lang} (ISO 639-1, e.g. en, hi, ta).
Return JSON only: {{"detected_source": "ISO 639-1 code", "translated": "translated text only"}}
Text:
{text}"""
        resp = model.generate_content(prompt)
        raw = (resp.text or "{}").strip()
        try:
            data = json.loads(raw)
            translated = str(data.get("translated", "")).strip()
            detected = str(data.get("detected_source", "unknown")).strip()
            if not translated:
                raise ValueError("empty translation")
            return translated, detected, detected, "gemini"
        except Exception as e:
            logger.warning("Gemini auto-translate JSON parse failed: %s", e)
            raise

    prompt = f"""Translate the following text from language code {source_lang} to language code {target_lang}.
Output ONLY the translated text, with no quotes or commentary.
Text:
{text}"""
    resp = model.generate_content(prompt)
    try:
        out = (resp.text or "").strip()
    except ValueError:
        out = ""
    if not out:
        raise RuntimeError("empty response")
    out = re.sub(r"^[\"']|[\"']$", "", out)
    return out, source_lang, None, "gemini"


def stub_translate(text: str, target_lang: str, source_lang: str) -> tuple[str, str, str | None, str]:
    return f"[{target_lang}] {text}", source_lang, None, "mock"

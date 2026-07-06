from __future__ import annotations

import logging

from app.core.config import Settings, settings
from app.services.evidence_media_service import gemini_configured

logger = logging.getLogger(__name__)

_SUPPORTED_AUDIO = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/mp4",
    "audio/m4a",
}


def _normalize_mime(mime: str | None, filename: str | None) -> str:
    raw = (mime or "").split(";")[0].strip().lower()
    if raw in _SUPPORTED_AUDIO:
        return raw
    name = (filename or "").lower()
    if name.endswith(".webm"):
        return "audio/webm"
    if name.endswith(".wav"):
        return "audio/wav"
    if name.endswith(".mp3"):
        return "audio/mpeg"
    if name.endswith(".ogg"):
        return "audio/ogg"
    return "audio/webm"


def transcribe_audio_bytes(
    data: bytes,
    *,
    mime_type: str | None = None,
    filename: str | None = None,
    language_hint: str = "auto",
    app_settings: Settings | None = None,
) -> tuple[str, str, str]:
    """
    Returns (transcript, detected_language, provider).
    Uses Gemini multimodal when configured; otherwise a short rule-based hint.
    """
    cfg = app_settings or settings
    mime = _normalize_mime(mime_type, filename)

    if not data:
        return "", language_hint or "en", "empty"

    if gemini_configured(cfg):
        try:
            import google.generativeai as genai

            genai.configure(api_key=cfg.gemini_api_key)
            model = genai.GenerativeModel(cfg.gemini_model_fast or cfg.gemini_model)
            lang_note = (
                "Detect language (ISO 639-1) and include Hindi/Hinglish if spoken."
                if language_hint == "auto"
                else f"Language hint: {language_hint}."
            )
            prompt = (
                "Transcribe the spoken audio for an India gig marketplace task description. "
                f"{lang_note} Return ONLY the transcript text, no quotes or labels."
            )
            resp = model.generate_content(
                [
                    prompt,
                    {"mime_type": mime, "data": data},
                ]
            )
            text = (resp.text or "").strip()
            if text:
                from app.services.beta_service import record_gemini_call

                record_gemini_call()
                return text, language_hint if language_hint != "auto" else "auto", "gemini"
        except Exception as exc:
            logger.warning("gemini transcribe failed: %s", exc)

    # Fallback when Gemini unavailable — keep poster flow usable in dev
    size_kb = max(1, len(data) // 1024)
    return (
        f"Voice note recorded ({size_kb} KB). Type or paste your task details here "
        f"— enable GEMINI_API_KEY and USE_MOCK_CHATBOT=false for real transcription.",
        language_hint or "en",
        "stub",
    )

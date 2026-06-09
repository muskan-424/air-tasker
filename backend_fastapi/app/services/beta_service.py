from __future__ import annotations

import re

from app.core.config import Settings, settings
from app.services.task_publish_service import PublishDraftError

_BETA_LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
}


def _split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def beta_categories(cfg: Settings | None = None) -> list[str]:
    return [c.lower() for c in _split_csv((cfg or settings).beta_categories)]


def beta_pin_codes(cfg: Settings | None = None) -> list[str]:
    return _split_csv((cfg or settings).beta_pin_codes)


def beta_languages(cfg: Settings | None = None) -> list[dict[str, str]]:
    cfg = cfg or settings
    return [
        {"code": code, "label": _BETA_LANGUAGE_LABELS.get(code, code.upper())}
        for code in _split_csv(cfg.beta_languages)
    ]


def beta_feature_flags(cfg: Settings | None = None) -> dict[str, bool]:
    cfg = cfg or settings
    return {
        "ai_chat": cfg.feature_flag_ai_chat,
        "voice_input": cfg.feature_flag_voice_input,
        "kyc_payout": cfg.feature_flag_kyc_payout,
        "razorpay_checkout": cfg.feature_flag_razorpay_checkout,
        "disputes": cfg.feature_flag_disputes,
    }


def beta_config_payload(cfg: Settings | None = None) -> dict:
    cfg = cfg or settings
    return {
        "beta_enabled": cfg.beta_mode_enabled,
        "city_label": cfg.beta_city_label,
        "categories": beta_categories(cfg),
        "pin_codes": beta_pin_codes(cfg),
        "languages": beta_languages(cfg),
        "feature_flags": beta_feature_flags(cfg),
        "feedback_path": "/feedback",
    }


def _normalize_category(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _extract_pin_from_schema(task_schema: dict) -> str | None:
    location = str(task_schema.get("location") or "")
    pins = re.findall(r"\b(\d{6})\b", location)
    return pins[0] if pins else None


def validate_draft_for_beta(ai_schema: dict, cfg: Settings | None = None) -> None:
    """Raise PublishDraftError when beta limits are violated."""
    cfg = cfg or settings
    if not cfg.beta_mode_enabled:
        return

    allowed_categories = beta_categories(cfg)
    category = _normalize_category(str(ai_schema.get("category", "general")))
    if allowed_categories and category not in allowed_categories:
        # Allow partial match (e.g. "electrical repair" contains electrical intent)
        if not any(cat in category or category in cat for cat in allowed_categories):
            raise PublishDraftError(
                "beta_category",
                f"Closed beta supports categories only: {', '.join(allowed_categories)}",
            )

    allowed_pins = beta_pin_codes(cfg)
    if not allowed_pins:
        return
    pin = _extract_pin_from_schema(ai_schema)
    if pin and pin not in allowed_pins:
        raise PublishDraftError(
            "beta_pin",
            f"Closed beta is limited to PIN codes: {', '.join(allowed_pins)} ({cfg.beta_city_label})",
        )


def record_gemini_call() -> None:
    from app.services.metrics_service import inc

    inc("gemini_calls_total")

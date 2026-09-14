from __future__ import annotations

import json
import logging
import re

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

_REQUIRED_KEYS = ("title", "description", "category")
_LOCATION_TYPES = ("IN_PERSON", "REMOTE")
_TIMING_TYPES = ("FLEXIBLE", "ON_DATE", "BEFORE_DATE")


def validate_task_schema(schema: dict) -> tuple[bool, list[str]]:
    """Validate structured task JSON before save/publish."""
    errors: list[str] = []
    if not isinstance(schema, dict):
        return False, ["schema must be a JSON object"]

    for key in _REQUIRED_KEYS:
        val = schema.get(key)
        if not val or not str(val).strip():
            errors.append(f"missing or empty {key}")

    price = schema.get("suggestedPriceRange")
    if not isinstance(price, dict):
        errors.append("suggestedPriceRange must be an object")
    else:
        try:
            min_p = int(price.get("min", 0))
            max_p = int(price.get("max", 0))
            if min_p <= 0 or max_p <= 0 or min_p > max_p:
                errors.append("suggestedPriceRange min/max invalid")
        except (TypeError, ValueError):
            errors.append("suggestedPriceRange min/max must be numbers")

    loc = schema.get("location")
    if loc is not None and str(loc).strip():
        pin = re.sub(r"\D", "", str(loc))
        if len(pin) != 6:
            errors.append("location should be a 6-digit India PIN when provided")

    location_type = schema.get("locationType")
    if location_type is not None and location_type not in _LOCATION_TYPES:
        errors.append(f"locationType must be one of {_LOCATION_TYPES}")

    timing = schema.get("timing")
    if timing is not None:
        if not isinstance(timing, dict):
            errors.append("timing must be an object")
        else:
            timing_type = timing.get("type")
            if timing_type not in _TIMING_TYPES:
                errors.append(f"timing.type must be one of {_TIMING_TYPES}")
            if timing_type in ("ON_DATE", "BEFORE_DATE"):
                date_val = timing.get("date")
                if not date_val or not _is_iso_date(str(date_val)):
                    errors.append("timing.date must be a YYYY-MM-DD date when timing.type needs one")

    return len(errors) == 0, errors


def _is_iso_date(value: str) -> bool:
    try:
        from datetime import date

        date.fromisoformat(value[:10])
        return True
    except ValueError:
        return False


def normalize_task_schema(raw: dict, source_text: str) -> dict:
    """Fill defaults and coerce types on Gemini or rule output."""
    price = raw.get("suggestedPriceRange") if isinstance(raw.get("suggestedPriceRange"), dict) else {}
    try:
        min_p = int(price.get("min", 500))
        max_p = int(price.get("max", 1200))
    except (TypeError, ValueError):
        min_p, max_p = 500, 1200
    if min_p > max_p:
        min_p, max_p = sorted([min_p, max_p])

    tools = raw.get("requiredTools")
    if not isinstance(tools, list):
        tools = [t.strip() for t in str(tools or "").split(",") if t.strip()]

    location = str(raw.get("location") or "").strip()
    if not location:
        pins = re.findall(r"\b(\d{6})\b", source_text)
        if pins:
            location = pins[0]

    location_type = str(raw.get("locationType") or "IN_PERSON").upper()
    if location_type not in _LOCATION_TYPES:
        location_type = "IN_PERSON"

    timing_raw = raw.get("timing") if isinstance(raw.get("timing"), dict) else {}
    timing_type = str(timing_raw.get("type") or "FLEXIBLE").upper()
    if timing_type not in _TIMING_TYPES:
        timing_type = "FLEXIBLE"
    timing_date = timing_raw.get("date")
    if timing_type in ("ON_DATE", "BEFORE_DATE") and not (timing_date and _is_iso_date(str(timing_date))):
        # No usable date was given, so there's nothing to be "on" or "before".
        timing_type = "FLEXIBLE"
        timing_date = None
    if timing_type == "FLEXIBLE":
        timing_date = None

    return {
        "title": str(raw.get("title") or source_text[:120]).strip(),
        "description": str(raw.get("description") or source_text).strip(),
        "language": str(raw.get("language") or "en")[:10],
        "category": str(raw.get("category") or "general").strip(),
        "urgencyLevel": str(raw.get("urgencyLevel") or "normal"),
        "location": location,
        "locationType": location_type,
        "timing": {"type": timing_type, "date": timing_date},
        "estimatedDurationMinutes": int(raw.get("estimatedDurationMinutes") or 60),
        "requiredTools": tools,
        "completionCriteria": str(
            raw.get("completionCriteria") or "Task completed as described by the poster."
        ),
        "evidenceRequirements": str(
            raw.get("evidenceRequirements") or "Before and after photos required."
        ),
        "suggestedPriceRange": {"min": min_p, "max": max_p, "currency": "INR"},
    }


def _today_iso() -> str:
    from datetime import date

    return date.today().isoformat()


def _gemini_configured(app_settings: Settings) -> bool:
    return bool(app_settings.gemini_api_key and not app_settings.use_mock_chatbot)


def _call_gemini_schema(text: str, *, retry_errors: list[str] | None, app_settings: Settings) -> dict | None:
    try:
        import google.generativeai as genai

        genai.configure(api_key=app_settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=app_settings.gemini_model_quality or app_settings.gemini_model,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )
        retry_note = ""
        if retry_errors:
            retry_note = f"\nPrevious JSON failed validation: {retry_errors}. Fix and return valid JSON only.\n"
        prompt = f"""Extract a structured gig task from the user message for an India marketplace.
Return JSON only with keys:
title, description, language (en or hi), category (plumbing|electrical|cleaning|tech|handyman|general),
urgencyLevel (normal|high), location (6-digit India PIN if mentioned, else empty string),
locationType ("REMOTE" if the work can be done online/over a call, else "IN_PERSON"),
timing (object: type is "ON_DATE" if a specific date is mentioned, "BEFORE_DATE" if a deadline is
mentioned, else "FLEXIBLE"; date is that date as YYYY-MM-DD, else null. Resolve relative dates like
"today"/"tomorrow" against today's date. Omit the date field, or set it null, when type is "FLEXIBLE"),
estimatedDurationMinutes (integer), requiredTools (array of strings),
completionCriteria, evidenceRequirements,
suggestedPriceRange (object with min, max integers in INR, currency INR).
Use realistic INR prices for Indian cities. Do not invent a PIN if none is given.{retry_note}
Today's date: {_today_iso()}
User message: {text!r}"""
        resp = model.generate_content(prompt)
        data = json.loads(resp.text or "{}")
        if not isinstance(data, dict):
            return None
        return normalize_task_schema(data, text)
    except Exception as e:
        logger.warning("gemini task schema failed: %s", e)
        return None


def build_task_schema_with_gemini(text: str, app_settings: Settings | None = None) -> tuple[dict | None, str]:
    """Try Gemini (with one validation retry), return (schema, provider)."""
    cfg = app_settings or settings
    if not _gemini_configured(cfg):
        return None, "rule"

    schema = _call_gemini_schema(text, retry_errors=None, app_settings=cfg)
    if schema is None:
        return None, "rule"

    ok, errors = validate_task_schema(schema)
    if ok:
        return schema, "gemini"

    schema = _call_gemini_schema(text, retry_errors=errors, app_settings=cfg)
    if schema is None:
        return None, "rule"

    ok, _ = validate_task_schema(schema)
    if ok:
        return schema, "gemini"
    return None, "rule"

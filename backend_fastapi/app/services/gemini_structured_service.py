from __future__ import annotations

import json
import logging
import re

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

_ALLOWED_INTENTS = (
    "order_lookup",
    "task_discovery",
    "task_creation_assistant",
    "apply_to_task",
    "publish_draft",
    "general_help",
)


def structured_intent_fallback(message: str) -> dict:
    m = message.lower()
    intent = "general_help"
    if "order" in m or "last" in m:
        intent = "order_lookup"
    elif "job" in m or "near" in m or "task" in m and "apply" not in m:
        intent = "task_discovery"
    elif "create task" in m or "post task" in m:
        intent = "task_creation_assistant"
    elif "apply" in m:
        intent = "apply_to_task"
    elif "publish" in m:
        intent = "publish_draft"
    uuids = re.findall(r"[0-9a-fA-F-]{36}", message)
    return {
        "intent": intent,
        "entities": {"uuids": uuids},
        "provider": "rule",
    }


def structured_intent_gemini(message: str, app_settings: Settings | None = None) -> dict | None:
    cfg = app_settings or settings
    if not cfg.gemini_api_key or cfg.use_mock_chatbot:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=cfg.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=cfg.gemini_model_fast or cfg.gemini_model,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=512,
                response_mime_type="application/json",
            ),
        )
        prompt = f"""Classify the user message for a gig marketplace chatbot.
Return JSON only with keys: intent (one of {list(_ALLOWED_INTENTS)}), entities (object, optional uuids as array of strings), language_guess (en or hi).
User message: {message!r}"""
        resp = model.generate_content(prompt)
        text = resp.text or "{}"
        data = json.loads(text)
        data["provider"] = "gemini"
        return data
    except Exception as e:
        logger.warning("structured_intent_gemini failed: %s", e)
        return None


def classify_message(message: str, app_settings: Settings | None = None) -> dict:
    g = structured_intent_gemini(message, app_settings)
    if g:
        return g
    return structured_intent_fallback(message)

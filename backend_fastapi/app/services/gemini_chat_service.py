from __future__ import annotations

import logging
import re

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

_SYSTEM = """You are the in-app assistant for an India-focused gig marketplace (tasks, escrow, disputes).
Rules:
- Use ONLY information provided in the FACTS block. Do not invent task IDs, prices, user data, or policies.
- Preserve every UUID exactly as given. Do not change numbers or dates from FACTS.
- Be concise, friendly, and practical. Hinglish is fine when the user message is Hindi-heavy.
- Do not give medical, legal, or investment advice. Do not ask for passwords or OTPs.
- If FACTS are empty or insufficient, say what you can and suggest next steps without making things up.
"""


def _gemini_configured(app_settings: Settings) -> bool:
    return bool(app_settings.gemini_api_key and not app_settings.use_mock_chatbot)


def select_model_for_synthesis(
    cfg: Settings,
    *,
    intent: str,
    user_message: str,
    facts_block: str,
) -> str:
    """Route longer / open-ended prompts to the quality model; keep short transactional paths on fast."""
    fast = cfg.gemini_model_fast or cfg.gemini_model
    quality = cfg.gemini_model_quality or cfg.gemini_model
    total = len(user_message) + len(facts_block)
    if total >= cfg.gemini_quality_min_total_chars:
        return quality
    if intent in ("general_help", "app_help", "task_creation_assistant") and len(user_message) > 500:
        return quality
    return fast


def select_model_for_refine(cfg: Settings, original_answer: str) -> str:
    fast = cfg.gemini_model_fast or cfg.gemini_model
    quality = cfg.gemini_model_quality or cfg.gemini_model
    if len(original_answer) >= 800:
        return quality
    return fast


def synthesize_reply(
    *,
    intent: str,
    user_message: str,
    facts_block: str,
    language: str = "en",
    tone: str = "friendly",
    app_settings: Settings | None = None,
) -> str | None:
    """Rewrite tool/RAG output into a natural reply. Returns None on failure (caller uses rule-based text)."""
    cfg = app_settings or settings
    if not _gemini_configured(cfg):
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=cfg.gemini_api_key)
        model_name = select_model_for_synthesis(
            cfg, intent=intent, user_message=user_message, facts_block=facts_block
        )
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=_SYSTEM,
            generation_config={
                "temperature": 0.35,
                "max_output_tokens": 1024,
            },
        )
        lang_note = (
            "Respond mostly in Hindi (Devanagari) mixed with English if language is hi or user wrote Hindi."
            if language.lower() in ("hi", "hin")
            else "Respond in clear English unless the user wrote Hindi; then use Hinglish."
        )
        tl = tone.lower()
        if tl == "professional":
            tone_note = "Tone: professional and neutral."
        elif tl == "concise":
            tone_note = "Tone: very concise (2–4 short sentences)."
        else:
            tone_note = "Tone: warm, friendly, approachable."
        prompt = f"""INTENT: {intent}
USER_MESSAGE: {user_message}
LANGUAGE_HINT: {language}. {lang_note}
{tone_note}

FACTS (authoritative, do not contradict):
{facts_block}

Write the assistant reply to the user."""
        resp = model.generate_content(prompt)
        try:
            text = (resp.text or "").strip()
        except ValueError:
            logger.warning("Gemini synthesize_reply: no text in response (blocked or empty)")
            return None
        if not text:
            return None
        return _strip_code_fence(text)
    except Exception as e:
        logger.warning("Gemini synthesize_reply failed: %s", e)
        return None


def refine_with_gemini(
    *,
    original_answer: str,
    instruction: str,
    language: str = "en",
    app_settings: Settings | None = None,
) -> str | None:
    cfg = app_settings or settings
    if not _gemini_configured(cfg):
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=cfg.gemini_api_key)
        model_name = select_model_for_refine(cfg, original_answer)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=_SYSTEM
            + "\nTask: rewrite ORIGINAL per INSTRUCTION only. Keep factual content; do not add new facts.",
            generation_config={"temperature": 0.3, "max_output_tokens": 2048},
        )
        prompt = f"""ORIGINAL:
{original_answer}

INSTRUCTION:
{instruction}

Preferred language code: {language}"""
        resp = model.generate_content(prompt)
        try:
            text = (resp.text or "").strip()
        except ValueError:
            logger.warning("Gemini refine: no text in response")
            return None
        if not text:
            return None
        return _strip_code_fence(text)
    except Exception as e:
        logger.warning("Gemini refine failed: %s", e)
        return None


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()

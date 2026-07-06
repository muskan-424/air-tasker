from __future__ import annotations

import json
import logging

from app.core.config import Settings, settings
from app.models.task import EvidenceUpload, VerificationStatus
from app.services.evidence_media_service import gemini_configured, load_image_bytes

logger = logging.getLogger(__name__)


def _mock_verification_status(evidence: EvidenceUpload) -> tuple[VerificationStatus, float, str]:
    has_before = bool(evidence.before_image_url)
    has_after = bool(evidence.after_image_url)
    has_video = bool(evidence.evidence_video_url)
    if has_before and has_after:
        return VerificationStatus.PASS, 0.92, "Before and after evidence available."
    if has_after or has_video:
        return VerificationStatus.LOW_CONFIDENCE, 0.62, "Partial evidence available; manual confirmation recommended."
    return VerificationStatus.FAIL, 0.18, "No sufficient completion evidence found."


def _status_from_confidence(confidence: float, cfg: Settings) -> VerificationStatus:
    if confidence >= cfg.verification_pass_confidence:
        return VerificationStatus.PASS
    if confidence >= cfg.verification_low_confidence:
        return VerificationStatus.LOW_CONFIDENCE
    return VerificationStatus.FAIL


def verify_evidence_with_gemini(
    evidence: EvidenceUpload,
    *,
    task_title: str | None = None,
    completion_criteria: str | None = None,
    app_settings: Settings | None = None,
) -> tuple[VerificationStatus, float, str, str]:
    """
    Returns (status, confidence, explanation, provider).
    """
    cfg = app_settings or settings
    if not gemini_configured(cfg):
        status, conf, expl = _mock_verification_status(evidence)
        return status, conf, expl, "rule"

    before = load_image_bytes(evidence.before_image_url)
    after = load_image_bytes(evidence.after_image_url)
    if not before or not after:
        status, conf, expl = _mock_verification_status(evidence)
        return status, conf, f"{expl} (Images must be uploaded via app for AI vision.)", "rule"

    try:
        import google.generativeai as genai

        genai.configure(api_key=cfg.gemini_api_key)
        model = genai.GenerativeModel(
            cfg.gemini_model_quality or cfg.gemini_model,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,
                response_mime_type="application/json",
            ),
        )
        title = task_title or "home service task"
        criteria = completion_criteria or "Work completed as described."
        prompt = f"""You are verifying gig work completion for an India marketplace.
Task: {title}
Completion criteria: {criteria}

Compare BEFORE and AFTER photos. Return JSON only:
{{"confidence": 0.0-1.0, "status": "PASS"|"LOW_CONFIDENCE"|"FAIL", "explanation": "one short sentence for the poster"}}

PASS = clear improvement matching the task. FAIL = unrelated images or no visible work. LOW_CONFIDENCE = ambiguous."""
        resp = model.generate_content(
            [
                prompt,
                "BEFORE image:",
                {"mime_type": before[1], "data": before[0]},
                "AFTER image:",
                {"mime_type": after[1], "data": after[0]},
            ]
        )
        data = json.loads(resp.text or "{}")
        confidence = float(data.get("confidence", 0))
        confidence = max(0.0, min(1.0, confidence))
        raw_status = str(data.get("status", "")).upper()
        if raw_status == "PASS":
            status = VerificationStatus.PASS
        elif raw_status == "FAIL":
            status = VerificationStatus.FAIL
        elif raw_status == "LOW_CONFIDENCE":
            status = VerificationStatus.LOW_CONFIDENCE
        else:
            status = _status_from_confidence(confidence, cfg)
        explanation = str(data.get("explanation") or "AI vision review completed.").strip()
        from app.services.beta_service import record_gemini_call

        record_gemini_call()
        return status, confidence, explanation, "gemini"
    except Exception as exc:
        logger.warning("gemini vision verify failed: %s", exc)
        status, conf, expl = _mock_verification_status(evidence)
        return status, conf, f"{expl} (Vision AI unavailable; using rules.)", "rule"


def resolve_verification(
    evidence: EvidenceUpload,
    *,
    task_schema: dict | None = None,
    app_settings: Settings | None = None,
) -> tuple[VerificationStatus, float, str, str]:
    schema = task_schema or {}
    return verify_evidence_with_gemini(
        evidence,
        task_title=str(schema.get("title") or ""),
        completion_criteria=str(schema.get("completionCriteria") or schema.get("completion_criteria") or ""),
        app_settings=app_settings,
    )

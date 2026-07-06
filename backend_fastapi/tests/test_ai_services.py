from app.models.task import EvidenceUpload, VerificationStatus
from app.services.gemini_vision_verification_service import resolve_verification
from app.services.gemini_voice_service import transcribe_audio_bytes


def test_transcribe_stub_when_gemini_off():
    text, lang, provider = transcribe_audio_bytes(b"\x00" * 2000, mime_type="audio/webm")
    assert provider == "stub"
    assert "Voice note" in text or len(text) > 0
    assert lang


def test_verify_rule_fallback_without_images():
    evidence = EvidenceUpload(
        before_image_url=None,
        after_image_url="https://example.com/after.jpg",
        evidence_video_url=None,
    )
    status, confidence, explanation, provider = resolve_verification(evidence)
    assert provider == "rule"
    assert status in {VerificationStatus.PASS, VerificationStatus.LOW_CONFIDENCE, VerificationStatus.FAIL}
    assert 0 <= confidence <= 1
    assert explanation

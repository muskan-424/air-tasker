from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.gemini_voice_service import transcribe_audio_bytes

router = APIRouter(prefix="/api/voice", tags=["voice"])


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str = Field(default="default", max_length=64)


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language_hint: str = "auto",
    current_user: User = Depends(get_current_user),
):
    """Speech-to-text via Gemini multimodal when configured; stub fallback otherwise."""
    _ = current_user.id
    data = await file.read()
    text, language, provider = transcribe_audio_bytes(
        data,
        mime_type=file.content_type,
        filename=file.filename,
        language_hint=language_hint,
    )
    return {
        "text": text,
        "language": language,
        "provider": provider,
    }


@router.post("/tts")
async def text_to_speech_stub(
    payload: TtsRequest,
    current_user: User = Depends(get_current_user),
):
    """TTS stub: returns metadata only (no audio bytes in MVP)."""
    _ = current_user.id
    return {
        "provider": "stub",
        "voice": payload.voice,
        "chars": len(payload.text),
        "note": "Integrate Google Cloud TTS or similar for audio URL.",
    }

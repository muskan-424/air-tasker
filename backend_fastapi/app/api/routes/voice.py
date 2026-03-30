from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User

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
    """Speech-to-text stub. Integrate Whisper / Google Speech-to-Text next."""
    _ = current_user.id
    data = await file.read()
    return {
        "text": f"[stub transcript from {file.filename or 'audio'}; bytes={len(data)}]",
        "language": language_hint,
        "provider": "stub",
        "note": "Replace with real STT (Whisper, Google STT, Bhashini).",
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

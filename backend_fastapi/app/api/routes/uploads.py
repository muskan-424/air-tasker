import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def _upload_dir() -> Path:
    root = Path(__file__).resolve().parents[3]
    path = root / settings.evidence_upload_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/evidence")
async def upload_evidence_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Store before/after photo or video locally; returns a URL for evidence API."""
    _ = current_user.id
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type or 'unknown'}. Use JPEG, PNG, WebP, MP4, or WebM.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > settings.evidence_max_file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {settings.evidence_max_file_bytes // (1024 * 1024)} MB)",
        )

    ext = EXT_BY_TYPE.get(content_type, Path(file.filename or "").suffix or ".bin")
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = _upload_dir() / filename
    dest.write_bytes(data)

    return {
        "url": f"/api/uploads/files/{filename}",
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(data),
    }


@router.get("/files/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded evidence files (UUID filenames are unguessable)."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    path = _upload_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(path)

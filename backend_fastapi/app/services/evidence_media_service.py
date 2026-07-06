from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _upload_root() -> Path:
    return Path(__file__).resolve().parents[2] / settings.evidence_upload_dir


def resolve_local_upload_path(url: str | None) -> Path | None:
    """Map /api/uploads/files/{name} to on-disk path."""
    if not url:
        return None
    marker = "/api/uploads/files/"
    if marker not in url:
        return None
    filename = url.split(marker, 1)[-1].split("?", 1)[0]
    if ".." in filename or "/" in filename or "\\" in filename:
        return None
    path = _upload_root() / filename
    return path if path.is_file() else None


def load_image_bytes(url: str | None) -> tuple[bytes, str] | None:
    """Load image bytes for vision models (local uploads only in MVP)."""
    path = resolve_local_upload_path(url)
    if not path:
        return None
    mime = _MIME_BY_EXT.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return path.read_bytes(), mime


def gemini_configured(app_settings: Settings | None = None) -> bool:
    cfg = app_settings or settings
    return bool(cfg.gemini_api_key and not cfg.use_mock_chatbot)

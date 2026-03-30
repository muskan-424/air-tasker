from fastapi import APIRouter
from datetime import UTC, datetime

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "healthy", "time": datetime.now(UTC).isoformat()}


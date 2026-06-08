from fastapi import APIRouter
from datetime import UTC, datetime

from app.core.config import settings

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "healthy", "time": datetime.now(UTC).isoformat()}


@router.get("/api/health/capabilities")
async def capabilities():
    gemini_on = bool(settings.gemini_api_key and not settings.use_mock_chatbot)
    pinecone_on = bool(
        settings.use_pinecone_rag and settings.pinecone_api_key and settings.pinecone_index
    )
    return {
        "environment": settings.environment,
        "use_mock_chatbot": settings.use_mock_chatbot,
        "gemini_enabled": gemini_on,
        "gemini_model_fast": settings.gemini_model_fast or settings.gemini_model,
        "pinecone_rag_enabled": pinecone_on,
        "task_schema_provider": "gemini" if gemini_on else "rule",
        "razorpay_configured": bool(settings.razorpay_key_id and settings.razorpay_key_secret),
    }

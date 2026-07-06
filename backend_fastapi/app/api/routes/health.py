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
    rag_mode = "pinecone" if pinecone_on else "local"
    return {
        "environment": settings.environment,
        "use_mock_chatbot": settings.use_mock_chatbot,
        "gemini_enabled": gemini_on,
        "gemini_model_fast": settings.gemini_model_fast or settings.gemini_model,
        "pinecone_rag_enabled": pinecone_on,
        "rag_mode": rag_mode,
        "rag_namespace": settings.pinecone_namespace,
        "task_schema_provider": "gemini" if gemini_on else "rule",
        "voice_stt_provider": "gemini" if gemini_on else "stub",
        "vision_verify_provider": "gemini" if gemini_on else "rule",
        "email_configured": bool(settings.smtp_host),
        "razorpay_configured": bool(settings.razorpay_key_id and settings.razorpay_key_secret),
    }


@router.get("/api/health/webhooks")
async def webhooks_readiness():
    """Readiness probe for webhook routes (no secrets exposed)."""
    return {
        "razorpay_webhook_secret_configured": bool(settings.razorpay_webhook_secret),
        "kyc_webhook_secret_configured": bool(settings.kyc_webhook_secret),
        "razorpay_webhook_path": "/api/webhooks/razorpay",
        "kyc_webhook_path": "/api/webhooks/kyc",
    }

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "airtasker-india-fastapi"
    environment: str = "development"
    port: int = 4000

    # Example: postgresql+asyncpg://postgres:password@localhost:5432/airtasker
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/airtasker"

    secret_key: str = "change-this-secret-in-production"
    access_token_expire_minutes: int = 60 * 24
    jwt_algorithm: str = "HS256"

    # Agentic chatbot + RAG config
    use_mock_chatbot: bool = True
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    # Latency vs quality: short/simple paths use fast model; long or complex use quality model.
    gemini_model_fast: str = "gemini-2.0-flash"
    gemini_model_quality: str = "gemini-2.0-flash"
    gemini_quality_min_total_chars: int = 1200  # user message + FACTS length threshold
    gemini_embedding_model: str = "models/text-embedding-004"
    agent_confidence_threshold: float = 0.45
    skip_gemini_on_low_confidence: bool = True
    low_confidence_append_note: bool = True
    use_pinecone_rag: bool = False
    pinecone_api_key: str | None = None
    pinecone_index: str | None = None
    pinecone_namespace: str = "airtasker-help"
    # 0 = disabled. When > 0 and USE_PINECONE_RAG, background task re-upserts docs every N hours.
    rag_reindex_interval_hours: int = 0

    # OTP / email (stub if SMTP not set)
    otp_ttl_seconds: int = 600
    otp_max_attempts: int = 5
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None

    # Redis (optional cache)
    redis_url: str | None = None

    # Razorpay (India payments; optional — order + webhook MVP)
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    # RazorpayX / Payouts: business account number from Dashboard (required to call POST /v1/payouts)
    razorpay_payout_account_number: str | None = None
    razorpay_webhook_secret: str | None = None
    # 0 = disable scheduled cleanup. Deletes rows from razorpay_webhook_events older than N days.
    razorpay_webhook_events_retention_days: int = 90
    # 0 = disable cleanup loop.
    razorpay_webhook_events_cleanup_interval_hours: int = 24

    # Notifications retry worker
    notification_retry_interval_seconds: int = 120
    notification_retry_batch_size: int = 50
    notification_retry_max_attempts: int = 5

    # Rate limits (SlowAPI; applied on auth + verification)
    rate_limit_default: str = "60/minute"
    rate_limit_auth: str = "15/minute"

    # Chat tone / i18n templates
    default_chat_tone: str = "friendly"

    # KYC (stub now; swap provider for Signzy / DigiLocker later)
    kyc_provider: str = "stub"
    # When true and provider is stub, submissions are auto-verified (dev/demo). Set false to require admin review.
    kyc_stub_auto_verify: bool = True
    # Optional HMAC for POST /api/webhooks/kyc (hex digest of raw body, same as Razorpay webhook style)
    kyc_webhook_secret: str | None = None
    # When true, taskers must have verified KYC to register payout bank details; escrow payout skips if not verified.
    kyc_required_for_payout: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


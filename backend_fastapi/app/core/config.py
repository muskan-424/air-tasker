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

    # Rate limits (SlowAPI; applied on auth + verification)
    rate_limit_default: str = "60/minute"
    rate_limit_auth: str = "15/minute"

    # Chat tone / i18n templates
    default_chat_tone: str = "friendly"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


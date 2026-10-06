import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Substrings that mark a SECRET_KEY as one of the placeholder values shipped in this repo's env templates.
_PLACEHOLDER_SECRET_MARKERS = ("change-this", "change-me", "replace-with", "do-not-use")


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

    # SMS OTP (stub if not set — no India gateway wired up yet)
    sms_gateway_url: str | None = None

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
    kyc_stub_auto_verify: bool = True
    # Optional HMAC for POST /api/webhooks/kyc (hex digest of raw body, same as Razorpay webhook style)
    kyc_webhook_secret: str | None = None
    # When true, taskers must have verified KYC to register payout bank details; escrow payout skips if not verified.
    kyc_required_for_payout: bool = False

    # Prometheus scrape endpoint GET /metrics (disable in locked-down prod if needed)
    enable_prometheus_metrics: bool = True

    # Comma-separated browser origins for CORS; use "*" only in local dev.
    cors_allowed_origins: str = "*"

    # Closed beta (Phase Y)
    beta_mode_enabled: bool = True
    beta_categories: str = "electrical,plumbing,cleaning,gardening,painting,handyman,tech,moving,tutoring,events"
    beta_pin_codes: str = "248001,110001,560001"
    beta_languages: str = "en,hi,ta"
    beta_city_label: str = "Dehradun · Delhi NCR · Bengaluru"
    beta_gemini_cost_inr_per_call: float = 0.25
    feature_flag_ai_chat: bool = True
    feature_flag_voice_input: bool = True
    feature_flag_kyc_payout: bool = True
    feature_flag_razorpay_checkout: bool = True
    feature_flag_disputes: bool = True

    # Marketplace: offers, service fees, cancellation
    # Legacy first-come /accept; production uses offers (tasker quotes, poster picks one).
    task_instant_accept_enabled: bool = False
    # Percent added on top of the task price and charged to the poster.
    poster_service_fee_percent: float = 5.0
    # Percent deducted from the task price before the tasker payout.
    tasker_service_fee_percent: float = 10.0
    # Floor applied to each non-zero service fee (INR).
    service_fee_min_inr: float = 10.0
    # Percent of the task price charged to whoever cancels after a tasker is assigned.
    cancellation_fee_percent: float = 10.0
    # Offer amount bounds (INR).
    offer_min_inr: float = 100.0
    offer_max_inr: float = 500000.0

    # Trust / fraud heuristics (Phase W)
    trust_cancel_window_days: int = 7
    trust_cancel_threshold: int = 3
    trust_evidence_fail_window_days: int = 30
    trust_evidence_fail_threshold: int = 2
    trust_new_account_days: int = 7
    trust_new_account_max_tasks_per_day: int = 8

    # Local evidence file uploads (MVP before S3 presign)
    evidence_upload_dir: str = "uploads/evidence"
    evidence_max_file_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Vision verification (Gemini when configured)
    verification_pass_confidence: float = 0.75
    verification_low_confidence: float = 0.45

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def cors_origins(self) -> list[str]:
        raw = self.cors_allowed_origins.strip()
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]

    def production_config_problems(self) -> tuple[list[str], list[str]]:
        """Return (errors, warnings) for settings that are unsafe when ENVIRONMENT=production.

        Errors make the app refuse to start (see enforce_production_config); warnings are only logged.
        Returns two empty lists outside production so dev, test, and staging are unaffected.
        """
        if self.environment.strip().lower() != "production":
            return [], []

        errors: list[str] = []
        warnings: list[str] = []

        key = self.secret_key.strip()
        lowered = key.lower()
        if len(key) < 32 or any(marker in lowered for marker in _PLACEHOLDER_SECRET_MARKERS):
            errors.append(
                "SECRET_KEY is missing, shorter than 32 characters, or still a placeholder — "
                "anyone who knows the placeholder can forge login tokens. Generate one with `openssl rand -hex 32`."
            )
        if "*" in self.cors_origins():
            errors.append(
                'CORS_ALLOWED_ORIGINS is "*" — set it to your frontend origin(s), e.g. https://app.example.com.'
            )

        if "postgres:postgres@" in self.database_url:
            warnings.append("DATABASE_URL uses the default postgres:postgres credentials.")
        if self.use_mock_chatbot:
            warnings.append("USE_MOCK_CHATBOT=true — the chatbot serves canned answers, not Gemini.")
        if self.kyc_provider.strip().lower() == "stub" and self.kyc_stub_auto_verify:
            warnings.append(
                "KYC_STUB_AUTO_VERIFY=true with the stub provider auto-verifies every user, so the payout KYC gate "
                "does nothing. Set KYC_STUB_AUTO_VERIFY=false to require admin approval, or wire a real provider."
            )
        if self.feature_flag_razorpay_checkout and not (self.razorpay_key_id and self.razorpay_key_secret):
            warnings.append("Razorpay checkout is enabled but RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are not set.")
        if not self.razorpay_webhook_secret:
            warnings.append("RAZORPAY_WEBHOOK_SECRET is not set — Razorpay webhooks will be rejected (503).")
        return errors, warnings

    def enforce_production_config(self) -> None:
        """Log warnings and raise RuntimeError on errors; a no-op outside production."""
        errors, warnings = self.production_config_problems()
        for message in warnings:
            logger.warning("Production config: %s", message)
        if errors:
            raise RuntimeError(
                "Refusing to start with an unsafe production configuration:\n  - " + "\n  - ".join(errors)
            )


settings = Settings()


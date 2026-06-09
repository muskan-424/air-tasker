from pydantic import BaseModel, Field


class BetaFeatureFlags(BaseModel):
    ai_chat: bool = True
    voice_input: bool = True
    kyc_payout: bool = True
    razorpay_checkout: bool = True
    disputes: bool = True


class BetaLanguage(BaseModel):
    code: str
    label: str


class BetaConfigResponse(BaseModel):
    beta_enabled: bool
    city_label: str
    categories: list[str]
    pin_codes: list[str]
    languages: list[BetaLanguage]
    feature_flags: BetaFeatureFlags
    feedback_path: str = "/feedback"


class BetaFeedbackRequest(BaseModel):
    category: str = Field(default="other", pattern="^(bug|feature|support|other)$")
    message: str = Field(min_length=5, max_length=4000)
    email: str | None = Field(default=None, max_length=320)
    page_path: str | None = Field(default=None, max_length=500)


class BetaFeedbackResponse(BaseModel):
    feedback_id: str
    status: str = "received"


class BetaKpiResponse(BaseModel):
    window: str
    published_tasks: int
    completed_tasks: int
    accepted_tasks: int
    accept_rate: float
    open_disputes: int
    escrow_tasks: int
    dispute_rate: float
    median_time_to_publish_seconds: float | None
    draft_count: int
    ai_calls_estimated: int
    ai_cost_inr_estimated: float
    beta_categories: list[str]
    beta_pin_codes: list[str]

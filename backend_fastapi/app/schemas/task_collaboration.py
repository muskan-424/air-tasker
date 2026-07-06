from pydantic import BaseModel, Field


class TaskScopeResponse(BaseModel):
    scope_id: str
    task_id: str
    status: str
    agreed_price: str
    currency: str
    scope_json: dict | None = None
    note: str | None = None
    proposed_by_id: str
    proposed_at: str
    agreed_at: str | None = None


class TaskScopeProposeRequest(BaseModel):
    agreed_price: float = Field(gt=0, le=1_000_000)
    currency: str = "INR"
    scope_json: dict | None = None
    note: str | None = Field(default=None, max_length=1000)


class TaskThreadMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    source_lang: str = "auto"
    target_lang: str = "en"


class TaskThreadMessageResponse(BaseModel):
    id: str
    task_id: str
    sender_id: str
    original_text: str
    translated_text: str | None = None
    source_lang: str
    target_lang: str
    translation_provider: str | None = None
    created_at: str


class TaskDetailResponse(BaseModel):
    id: str
    poster_id: str
    tasker_id: str | None = None
    status: str
    category: str
    subcategory: str | None = None
    task_schema: dict
    scope: TaskScopeResponse | None = None
    escrow_status: str | None = None
    escrow_amount: str | None = None
    has_evidence: bool = False
    verification_status: str | None = None

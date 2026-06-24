from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    reported_user_id: str | None = None
    task_id: str | None = None
    category: str = Field(default="other", pattern="^(spam|harassment|fraud|safety|other)$")
    reason: str = Field(min_length=10, max_length=2000)


class ReportCreateResponse(BaseModel):
    report_id: str
    status: str
    trust_flags_raised: list[str] = []


class ReportListItem(BaseModel):
    report_id: str
    reporter_id: str
    reported_user_id: str | None
    task_id: str | None
    category: str
    reason: str
    status: str
    created_at: str


class ReportResolveRequest(BaseModel):
    outcome: str = Field(pattern="^(reviewed|dismissed)$")
    admin_notes: str | None = Field(default=None, max_length=2000)


class TrustFlagItem(BaseModel):
    flag_id: str
    user_id: str
    rule_code: str
    severity: str
    status: str
    details: dict | None
    created_at: str

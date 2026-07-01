from pydantic import BaseModel, Field


class TaskRateRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class TaskRatingResponse(BaseModel):
    rating_id: str
    task_id: str
    rater_id: str
    ratee_id: str
    score: int
    comment: str | None = None
    created_at: str


class UserRatingSummaryResponse(BaseModel):
    user_id: str
    average_score: float | None = None
    rating_count: int = 0

from pydantic import BaseModel, Field


class TaskDraftCreateRequest(BaseModel):
    raw_input: str = Field(min_length=3, max_length=2000)
    language: str | None = Field(default="en", max_length=10)


class TaskDraftResponse(BaseModel):
    id: str
    poster_id: str
    status: str
    ai_schema: dict
    ai_explain: str | None = None


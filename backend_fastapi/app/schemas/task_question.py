from pydantic import BaseModel, Field


class TaskQuestionCreateRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class TaskQuestionAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class TaskQuestionResponse(BaseModel):
    id: str
    task_id: str
    asker_id: str
    asker_display_name: str | None = None
    question: str
    answer: str | None = None
    answered_at: str | None = None
    created_at: str

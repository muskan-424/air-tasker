from pydantic import BaseModel, Field


class ChatTranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    source_lang: str = Field(default="auto", max_length=10)
    target_lang: str = Field(default="en", max_length=10)


class ChatTranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    provider: str
    note: str | None = None
    # When request had source_lang=auto, filled with detected ISO-style code (e.g. hi, en)
    detected_source_lang: str | None = None


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", max_length=10)
    session_id: str | None = None
    # friendly | professional | concise — guides Gemini system prompt when enabled
    tone: str = Field(default="friendly", max_length=32)


class AgentClassifyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentToolTrace(BaseModel):
    name: str
    used: bool
    details: str | None = None


class AgentChatResponse(BaseModel):
    reply: str
    intent: str
    session_id: str | None = None
    follow_up_required: bool = False
    suggested_actions: list[str] = []
    tool_traces: list[AgentToolTrace] = []
    # "gemini" when final text was produced by Gemini; "rule" when rule-based only
    llm_provider: str | None = None
    # Heuristic 0..1; below threshold may skip LLM polish and flag verification
    confidence: float = 0.7
    needs_verification: bool = False


class ChatRefineRequest(BaseModel):
    original_answer: str = Field(min_length=1, max_length=8000)
    instruction: str = Field(min_length=1, max_length=500)
    language: str = Field(default="en", max_length=10)


class ChatRefineResponse(BaseModel):
    refined_answer: str


class ChatHistoryMessage(BaseModel):
    role: str
    text: str
    intent: str | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatHistoryMessage]


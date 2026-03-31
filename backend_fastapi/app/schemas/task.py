from pydantic import BaseModel


class PublishTaskResponse(BaseModel):
    id: str
    poster_id: str
    status: str
    category: str
    subcategory: str | None = None
    task_schema: dict


class TaskFeedItem(BaseModel):
    id: str
    poster_id: str
    status: str
    category: str
    subcategory: str | None = None
    task_schema: dict


class AcceptTaskRequest(BaseModel):
    acknowledge_requirements: bool = True
    acknowledgement: dict | None = None


class AcceptTaskResponse(BaseModel):
    acceptance_id: str
    task_id: str
    tasker_id: str
    status: str


class EvidenceUploadRequest(BaseModel):
    before_image_url: str | None = None
    after_image_url: str | None = None
    evidence_video_url: str | None = None
    evidence_json: dict | None = None


class EvidenceUploadResponse(BaseModel):
    evidence_id: str
    task_id: str
    uploaded_by_id: str


class VerificationResponse(BaseModel):
    verification_id: str
    task_id: str
    status: str
    confidence: float
    explanation: str | None = None


class EscrowStartResponse(BaseModel):
    escrow_payment_id: str
    task_id: str
    status: str
    amount: str
    currency: str


class DisputeCreateRequest(BaseModel):
    reason: str | None = None


class DisputeCreateResponse(BaseModel):
    dispute_id: str
    task_id: str
    status: str


class EscrowReleaseResponse(BaseModel):
    escrow_payment_id: str
    task_id: str
    status: str
    payout_status: str | None = None


class DisputeResolveRequest(BaseModel):
    outcome: str = "release"  # release | cancel
    note: str | None = None


class DisputeResolveResponse(BaseModel):
    dispute_id: str
    status: str
    escrow_status: str | None = None


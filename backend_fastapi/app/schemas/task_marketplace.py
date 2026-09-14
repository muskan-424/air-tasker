from pydantic import BaseModel, Field


class FeeBreakdownResponse(BaseModel):
    task_price: str
    poster_fee: str
    poster_total: str
    tasker_fee: str
    tasker_payout: str


class OfferCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    message: str | None = Field(default=None, max_length=1000)


class OfferResponse(BaseModel):
    offer_id: str
    task_id: str
    tasker_id: str
    amount: str
    currency: str
    message: str | None = None
    status: str
    created_at: str
    updated_at: str
    tasker_display_name: str | None = None
    tasker_rating_average: float | None = None
    tasker_rating_count: int = 0
    fees: FeeBreakdownResponse


class OfferAcceptResponse(BaseModel):
    task_id: str
    task_status: str
    offer: OfferResponse


class CancelTaskRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class CancelTaskResponse(BaseModel):
    task_id: str
    status: str
    cancelled_by: str
    previous_status: str
    reason: str | None = None
    fee_amount: str
    refund_amount: str | None = None
    refund_status: str | None = None
    created_at: str

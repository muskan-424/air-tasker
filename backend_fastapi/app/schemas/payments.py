import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class RazorpayOrderRequest(BaseModel):
    task_id: uuid.UUID


class RazorpayOrderResponse(BaseModel):
    order_id: str
    amount: str
    amount_paise: int
    currency: str
    key_id: str
    escrow_id: str
    task_id: str


class RazorpayRefundRequest(BaseModel):
    task_id: uuid.UUID
    amount_inr: Decimal | None = Field(
        default=None,
        description="Partial refund in INR (paise rounded). Omit for full refund.",
    )


class RazorpayRefundResponse(BaseModel):
    issued: bool
    refund_id: str | None = None
    skipped_reason: str | None = None


class RegisterBankPayoutRequest(BaseModel):
    beneficiary_name: str = Field(..., min_length=2, max_length=120)
    ifsc: str = Field(..., min_length=11, max_length=15)
    account_number: str = Field(..., min_length=9, max_length=24)

    @field_validator("ifsc", mode="before")
    @classmethod
    def normalize_ifsc(cls, v: object) -> str:
        return "".join(str(v).split()).upper()

    @field_validator("account_number", mode="before")
    @classmethod
    def normalize_account(cls, v: object) -> str:
        return "".join(c for c in str(v) if c.isdigit())


class RegisterBankPayoutResponse(BaseModel):
    contact_id: str
    fund_account_id: str


class EscrowPayoutInitiateRequest(BaseModel):
    task_id: uuid.UUID


class EscrowPayoutInitiateResponse(BaseModel):
    status: str

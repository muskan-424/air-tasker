import re

from pydantic import BaseModel, Field, field_validator

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


class KycSubmitRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    pan: str = Field(..., min_length=10, max_length=10, description="10-character PAN; only last 4 digits are stored")
    aadhaar_last4: str | None = Field(default=None, min_length=4, max_length=4)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, v: object) -> str:
        s = str(v).strip()
        if len(s) < 2:
            raise ValueError("full_name too short")
        return s

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        p = str(v).upper().strip()
        if not PAN_RE.match(p):
            raise ValueError("invalid_pan_format")
        return p

    @field_validator("aadhaar_last4", mode="before")
    @classmethod
    def digits_aadhaar(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        d = "".join(c for c in str(v) if c.isdigit())
        if len(d) != 4:
            raise ValueError("aadhaar_last4 must be 4 digits")
        return d


class KycStatusResponse(BaseModel):
    status: str
    user_id: str | None = None
    provider: str | None = None
    full_name: str | None = None
    pan_masked: str | None = None
    aadhaar_last4: str | None = None
    submitted_at: str | None = None
    verified_at: str | None = None
    rejected_at: str | None = None
    rejection_reason: str | None = None


class KycAdminReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = Field(default=None, max_length=500)


def pan_to_last4(pan: str) -> str:
    if not PAN_RE.match(pan):
        raise ValueError("invalid_pan_format")
    return pan[5:9]

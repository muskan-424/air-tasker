from pydantic import BaseModel, Field

from app.models.platform_security import OtpPurpose


class OtpRequestBody(BaseModel):
    purpose: OtpPurpose = Field(description="EMAIL_VERIFICATION or SENSITIVE_ACTION")


class OtpVerifyBody(BaseModel):
    purpose: OtpPurpose
    code: str = Field(min_length=4, max_length=12)


class TrustedDeviceRegister(BaseModel):
    fingerprint: str = Field(min_length=8, max_length=128)
    label: str | None = Field(default=None, max_length=120)

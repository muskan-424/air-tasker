from pydantic import BaseModel, Field, field_validator

from app.services.pin_utils import normalize_india_pin, normalize_pin_list


class UserMeResponse(BaseModel):
    id: str
    email: str
    role: str
    email_verified_at: str | None = None


class UserProfileResponse(BaseModel):
    user_id: str
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    default_location_pin: str | None = None
    skills: list[str] = []
    service_pin_codes: list[str] = []
    preferred_languages: list[str] = ["en"]
    rating_average: float | None = None
    rating_count: int = 0


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)
    avatar_url: str | None = Field(default=None, max_length=500)
    default_location_pin: str | None = Field(default=None, max_length=6)
    skills: list[str] = Field(default_factory=list, max_length=20)
    service_pin_codes: list[str] = Field(default_factory=list, max_length=20)
    preferred_languages: list[str] = Field(default_factory=lambda: ["en"], max_length=10)

    @field_validator("default_location_pin")
    @classmethod
    def validate_default_pin(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return normalize_india_pin(value)

    @field_validator("service_pin_codes")
    @classmethod
    def validate_service_pins(cls, value: list[str]) -> list[str]:
        return normalize_pin_list(value)

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, value: list[str]) -> list[str]:
        cleaned = [s.strip() for s in value if s and s.strip()]
        return cleaned[:20]

    @field_validator("preferred_languages")
    @classmethod
    def validate_languages(cls, value: list[str]) -> list[str]:
        cleaned = [lang.strip().lower()[:10] for lang in value if lang and lang.strip()]
        return cleaned[:10] or ["en"]

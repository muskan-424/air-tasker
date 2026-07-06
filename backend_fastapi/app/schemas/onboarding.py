from pydantic import BaseModel


class OnboardingStep(BaseModel):
    id: str
    title: str
    description: str
    complete: bool
    href: str | None = None
    optional: bool = False


class OnboardingResponse(BaseModel):
    role: str
    complete: bool
    completed_count: int
    total_count: int
    steps: list[OnboardingStep]
    beta_pin_codes: list[str] = []
    beta_categories: list[str] = []

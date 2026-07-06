from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.kyc import KycStatus, UserKycProfile
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.schemas.onboarding import OnboardingResponse, OnboardingStep


def _beta_pins() -> list[str]:
    return [p.strip() for p in settings.beta_pin_codes.split(",") if p.strip()]


def _beta_categories() -> list[str]:
    return [c.strip() for c in settings.beta_categories.split(",") if c.strip()]


def _valid_pin(pin: str | None) -> bool:
    if not pin:
        return False
    return bool(re.fullmatch(r"\d{6}", str(pin).strip()))


async def build_onboarding_status(db: AsyncSession, user: User) -> OnboardingResponse:
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()

    email_ok = user.email_verified_at is not None
    display_name = (profile.display_name or "").strip() if profile else ""
    default_pin = (profile.default_location_pin or "").strip() if profile else ""
    skills = list(profile.skills or []) if profile else []
    service_pins = list(profile.service_pin_codes or []) if profile else []
    beta_pins = _beta_pins()

    steps: list[OnboardingStep] = []

    steps.append(
        OnboardingStep(
            id="email",
            title="Verify your email",
            description="Confirm your email with a 6-digit code so we can reach you about tasks and payments.",
            complete=email_ok,
            href="/account",
        )
    )

    if user.role == UserRole.TASKER:
        profile_ok = bool(display_name) and len(skills) >= 1 and any(_valid_pin(p) for p in service_pins)
        steps.append(
            OnboardingStep(
                id="tasker_profile",
                title="Set skills and service PINs",
                description=(
                    "Add at least one skill and a 6-digit PIN where you work. "
                    f"Beta areas: {', '.join(beta_pins) or 'see profile'}."
                ),
                complete=profile_ok,
                href="/profile",
            )
        )

        kyc = (
            await db.execute(select(UserKycProfile).where(UserKycProfile.user_id == user.id))
        ).scalar_one_or_none()
        kyc_ok = kyc is not None and kyc.status == KycStatus.VERIFIED
        steps.append(
            OnboardingStep(
                id="kyc",
                title="Complete KYC",
                description="Identity check for payouts (stub auto-verify in dev).",
                complete=kyc_ok,
                href="/kyc",
                optional=not settings.kyc_required_for_payout,
            )
        )

        payout_ok = bool(user.razorpay_fund_account_id)
        steps.append(
            OnboardingStep(
                id="payout",
                title="Link bank account",
                description="Register payout details so you get paid after verified jobs.",
                complete=payout_ok,
                href="/kyc",
                optional=True,
            )
        )

        steps.append(
            OnboardingStep(
                id="first_job",
                title="Browse the tasker radar",
                description="Accept a job in your PIN area and agree on price with the poster.",
                complete=False,
                href="/tasker",
                optional=True,
            )
        )
    else:
        poster_profile_ok = bool(display_name) and _valid_pin(default_pin)
        steps.append(
            OnboardingStep(
                id="poster_profile",
                title="Add your name and home PIN",
                description=(
                    "Posters need a default PIN for task location. "
                    f"Beta PINs: {', '.join(beta_pins) or '6-digit India PIN'}."
                ),
                complete=poster_profile_ok,
                href="/profile",
            )
        )
        steps.append(
            OnboardingStep(
                id="first_task",
                title="Post your first task",
                description="Describe a job in Hindi or English — AI builds the draft for you.",
                complete=False,
                href="/poster",
                optional=True,
            )
        )

    required = [s for s in steps if not s.optional]
    completed = sum(1 for s in required if s.complete)
    all_complete = all(s.complete for s in required)

    return OnboardingResponse(
        role=user.role.value,
        complete=all_complete,
        completed_count=completed,
        total_count=len(required),
        steps=steps,
        beta_pin_codes=beta_pins,
        beta_categories=_beta_categories(),
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileResponse, UserProfileUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_response(profile: UserProfile) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        default_location_pin=profile.default_location_pin,
        skills=list(profile.skills or []),
        service_pin_codes=list(profile.service_pin_codes or []),
        preferred_languages=list(profile.preferred_languages or ["en"]),
    )


async def _get_or_create_profile(db: AsyncSession, user: User) -> UserProfile:
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile:
        return profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await _get_or_create_profile(db, current_user)
    return _to_response(profile)


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await _get_or_create_profile(db, current_user)
    data = payload.model_dump()
    for key, value in data.items():
        setattr(profile, key, value)
    try:
        await db.commit()
        await db.refresh(profile)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_response(profile)

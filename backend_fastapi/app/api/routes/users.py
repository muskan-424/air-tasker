import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.ratings import UserRatingSummaryResponse
from app.schemas.user_profile import UserMeResponse, UserProfileResponse, UserProfileUpdateRequest
from app.services.rating_service import get_user_rating_summary

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_response(profile: UserProfile, *, rating_average: float | None = None, rating_count: int = 0) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        default_location_pin=profile.default_location_pin,
        skills=list(profile.skills or []),
        service_pin_codes=list(profile.service_pin_codes or []),
        preferred_languages=list(profile.preferred_languages or ["en"]),
        rating_average=rating_average,
        rating_count=rating_count,
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


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role.value,
        email_verified_at=current_user.email_verified_at.isoformat() if current_user.email_verified_at else None,
    )


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await _get_or_create_profile(db, current_user)
    avg, count = await get_user_rating_summary(db, current_user.id)
    return _to_response(profile, rating_average=avg, rating_count=count)


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
    avg, count = await get_user_rating_summary(db, current_user.id)
    return _to_response(profile, rating_average=avg, rating_count=count)


@router.get("/{user_id}/ratings-summary", response_model=UserRatingSummaryResponse)
async def get_user_ratings_summary(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")
    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    avg, count = await get_user_rating_summary(db, user_uuid)
    return UserRatingSummaryResponse(user_id=str(user_uuid), average_score=avg, rating_count=count)

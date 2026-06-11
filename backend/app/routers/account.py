from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.app.core.deps import get_current_user
from backend.app.core.rate_limit import limiter
from backend.app.db.models import User, UserSettings
from backend.app.db.session import get_db
from backend.app.schemas.settings import UserSettingsRequest, UserSettingsResponse
from backend.app.schemas.user import AppleUserResponse, UpdateProfileRequest
from backend.app.services.user_profile_service import build_user_response


router = APIRouter()


@router.get("/profile", response_model=AppleUserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_user_response(db=db, user=current_user)


@limiter.limit("30/minute")
@router.put("/profile", response_model=AppleUserResponse)
async def update_profile(
    request: Request,
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    display_name = data.displayName.strip()

    if len(display_name) < 2:
        raise HTTPException(status_code=400, detail="Display name is too short")

    if len(display_name) > 40:
        raise HTTPException(status_code=400, detail="Display name is too long")

    current_user.display_name = display_name
    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_user)

    return build_user_response(db=db, user=current_user)


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()

    if settings is None:
        return {
            "selectedGroupId": None,
            "selectedGroupName": None,
            "scheduleCacheWeeks": 2,
            "liveActivityEnabled": True,
        }

    return {
        "selectedGroupId": settings.selected_group_id,
        "selectedGroupName": settings.selected_group_name,
        "scheduleCacheWeeks": settings.schedule_cache_weeks,
        "liveActivityEnabled": settings.live_activity_enabled,
    }


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
    data: UserSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()

    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if data.selectedGroupId is not None:
        settings.selected_group_id = data.selectedGroupId
    if data.selectedGroupName is not None:
        settings.selected_group_name = data.selectedGroupName
    if data.scheduleCacheWeeks is not None:
        settings.schedule_cache_weeks = data.scheduleCacheWeeks
    if data.liveActivityEnabled is not None:
        settings.live_activity_enabled = data.liveActivityEnabled

    settings.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(settings)

    return {
        "selectedGroupId": settings.selected_group_id,
        "selectedGroupName": settings.selected_group_name,
        "scheduleCacheWeeks": settings.schedule_cache_weeks,
        "liveActivityEnabled": settings.live_activity_enabled,
    }

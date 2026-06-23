from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.deps import get_current_user, is_admin, is_moderator
from app.core.rate_limit import limiter
from app.db.models import User, UserSettings
from app.db.session import get_db
from app.schemas.settings import UserSettingsRequest, UserSettingsResponse
from app.schemas.user import AppleUserResponse, UpdateNameRequest, UpdateProfileRequest
from app.services.user_profile_service import build_user_response


router = APIRouter()


def _validate_display_name(value: str | None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="Name is required")

    display_name = value.strip()

    if len(display_name) < 2:
        raise HTTPException(status_code=400, detail="Display name is too short")

    if len(display_name) > 40:
        raise HTTPException(status_code=400, detail="Display name is too long")

    return display_name


def _save_display_name(
    db: Session,
    user: User,
    display_name: str,
) -> AppleUserResponse:
    user.display_name = display_name
    user.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)

    return build_user_response(db=db, user=user)


@router.get("/me", response_model=AppleUserResponse)
@router.get("/profile", response_model=AppleUserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_user_response(db=db, user=current_user)


@limiter.limit("30/minute")
@router.patch("/me", response_model=AppleUserResponse)
async def update_me(
    request: Request,
    data: UpdateNameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    display_name = _validate_display_name(data.name)
    return _save_display_name(db=db, user=current_user, display_name=display_name)


@limiter.limit("30/minute")
@router.put("/profile", response_model=AppleUserResponse)
async def update_profile(
    request: Request,
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    display_name = _validate_display_name(data.displayName)
    return _save_display_name(db=db, user=current_user, display_name=display_name)


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
    provided_fields = getattr(
        data,
        "model_fields_set",
        getattr(data, "__fields_set__", set()),
    )

    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()

    if settings is None:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if "selectedGroupId" in provided_fields:
        is_group_change = (
            settings.selected_group_id is not None
            and settings.selected_group_id != data.selectedGroupId
        )
        if is_group_change and not (
            is_admin(db=db, user=current_user)
            or is_moderator(db=db, user=current_user)
        ):
            raise HTTPException(
                status_code=409,
                detail="Group change requires moderator approval",
            )

        settings.selected_group_id = data.selectedGroupId
    if "selectedGroupName" in provided_fields:
        settings.selected_group_name = data.selectedGroupName
    if "scheduleCacheWeeks" in provided_fields and data.scheduleCacheWeeks is not None:
        settings.schedule_cache_weeks = data.scheduleCacheWeeks
    if "liveActivityEnabled" in provided_fields and data.liveActivityEnabled is not None:
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

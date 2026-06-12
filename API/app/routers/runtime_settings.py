from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, is_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.runtime_settings import (
    AppSettingAdminResponse,
    PublicConfigResponse,
    UpdateAppSettingRequest,
)
from app.services import runtime_settings_service


router = APIRouter()


def _require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/admin/settings", response_model=list[AppSettingAdminResponse])
def admin_list_settings(
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    return runtime_settings_service.list_admin_settings(db=db)


@router.patch("/admin/settings/{key}", response_model=AppSettingAdminResponse)
def admin_update_setting(
    key: str,
    payload: UpdateAppSettingRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    return runtime_settings_service.update_setting(
        db=db,
        key=key,
        value=payload.value,
        description=payload.description,
        is_public=payload.isPublic,
        updated_by=admin_user.id,
    )


@router.get("/config/public", response_model=PublicConfigResponse)
def get_public_config(
    db: Session = Depends(get_db),
):
    return {
        "settings": runtime_settings_service.get_public_config(db=db),
    }

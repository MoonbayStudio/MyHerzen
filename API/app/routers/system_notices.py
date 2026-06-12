from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, is_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.system_notices import (
    ActiveSystemNoticeResponse,
    SystemNoticeCreateRequest,
    SystemNoticeResponse,
    SystemNoticeUpdateRequest,
)
from app.schemas.user import SuccessResponse
from app.services import system_notices_service


router = APIRouter()


def _require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/system/notice", response_model=ActiveSystemNoticeResponse)
def get_active_system_notice(
    db: Session = Depends(get_db),
):
    return system_notices_service.get_active_notice_payload(db=db)


@router.get("/admin/system-notices", response_model=list[SystemNoticeResponse])
def admin_list_system_notices(
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    return system_notices_service.list_notices(db=db)


@router.post("/admin/system-notices", response_model=SystemNoticeResponse)
def admin_create_system_notice(
    payload: SystemNoticeCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    return system_notices_service.create_notice(
        db=db,
        title=payload.title,
        message=payload.message,
        notice_type=payload.type,
        is_active=payload.isActive,
        starts_at=payload.startsAt,
        ends_at=payload.endsAt,
        show_as=payload.showAs,
        dismissible=payload.dismissible,
        created_by=admin_user.id,
    )


@router.patch("/admin/system-notices/{notice_id}", response_model=SystemNoticeResponse)
def admin_update_system_notice(
    notice_id: int,
    payload: SystemNoticeUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    changes = payload.dict(exclude_unset=True)
    return system_notices_service.update_notice(
        db=db,
        notice_id=notice_id,
        changes=changes,
    )


@router.delete("/admin/system-notices/{notice_id}", response_model=SuccessResponse)
def admin_delete_system_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    system_notices_service.delete_notice(db=db, notice_id=notice_id)
    return {"success": True}


@router.post("/admin/system-notices/{notice_id}/activate", response_model=SystemNoticeResponse)
def admin_activate_system_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    return system_notices_service.set_notice_active_status(
        db=db,
        notice_id=notice_id,
        is_active=True,
    )


@router.post("/admin/system-notices/{notice_id}/deactivate", response_model=SystemNoticeResponse)
def admin_deactivate_system_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    return system_notices_service.set_notice_active_status(
        db=db,
        notice_id=notice_id,
        is_active=False,
    )

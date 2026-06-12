from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import SystemNotice
from app.repositories import system_notices_repository


_ALLOWED_NOTICE_TYPES = {"info", "warning", "maintenance", "critical"}
_ALLOWED_SHOW_AS = {"banner", "modal"}


def _normalize_notice_type(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in _ALLOWED_NOTICE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid notice type")
    return normalized


def _normalize_show_as(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in _ALLOWED_SHOW_AS:
        raise HTTPException(status_code=400, detail="Invalid notice display type")
    return normalized


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_notice_window(starts_at: Optional[datetime], ends_at: Optional[datetime]) -> None:
    if starts_at is None or ends_at is None:
        return
    if ends_at < starts_at:
        raise HTTPException(status_code=400, detail="endsAt must be greater than or equal to startsAt")


def serialize_notice(notice: SystemNotice) -> dict[str, Any]:
    return {
        "id": notice.id,
        "title": notice.title,
        "message": notice.message,
        "type": notice.type,
        "isActive": bool(notice.is_active),
        "startsAt": notice.starts_at,
        "endsAt": notice.ends_at,
        "showAs": notice.show_as,
        "dismissible": bool(notice.dismissible),
        "createdAt": notice.created_at,
        "updatedAt": notice.updated_at,
        "createdBy": notice.created_by,
    }


def serialize_public_notice(notice: SystemNotice) -> dict[str, Any]:
    return {
        "id": notice.id,
        "title": notice.title,
        "message": notice.message,
        "type": notice.type,
        "showAs": notice.show_as,
        "dismissible": bool(notice.dismissible),
        "startsAt": notice.starts_at,
        "endsAt": notice.ends_at,
    }


def list_notices(db: Session) -> list[dict[str, Any]]:
    notices = system_notices_repository.list_notices(db=db)
    return [serialize_notice(notice) for notice in notices]


def get_active_notice_payload(db: Session) -> dict[str, Any]:
    notice = system_notices_repository.get_active_notice(db=db)
    if notice is None:
        return {"isActive": False, "notice": None}
    return {
        "isActive": True,
        "notice": serialize_public_notice(notice),
    }


def create_notice(
    db: Session,
    title: str,
    message: str,
    notice_type: str,
    is_active: bool,
    starts_at: Optional[datetime],
    ends_at: Optional[datetime],
    show_as: str,
    dismissible: bool,
    created_by: Optional[int],
) -> dict[str, Any]:
    normalized_title = (title or "").strip()
    normalized_message = (message or "").strip()

    if not normalized_title:
        raise HTTPException(status_code=400, detail="title is required")

    if not normalized_message:
        raise HTTPException(status_code=400, detail="message is required")

    normalized_starts_at = _normalize_datetime(starts_at)
    normalized_ends_at = _normalize_datetime(ends_at)
    _validate_notice_window(normalized_starts_at, normalized_ends_at)

    now = datetime.now(timezone.utc)
    notice = system_notices_repository.create_notice(
        db=db,
        title=normalized_title,
        message=normalized_message,
        notice_type=_normalize_notice_type(notice_type),
        is_active=bool(is_active),
        starts_at=normalized_starts_at,
        ends_at=normalized_ends_at,
        show_as=_normalize_show_as(show_as),
        dismissible=bool(dismissible),
        created_by=created_by,
        now=now,
    )
    db.commit()
    db.refresh(notice)
    return serialize_notice(notice)


def update_notice(
    db: Session,
    notice_id: int,
    changes: dict[str, Any],
) -> dict[str, Any]:
    notice = system_notices_repository.get_notice_by_id(db=db, notice_id=notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="System notice not found")

    if "title" in changes:
        title = changes.get("title")
        if not isinstance(title, str):
            raise HTTPException(status_code=400, detail="title must be a string")
        normalized_title = title.strip()
        if not normalized_title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        notice.title = normalized_title

    if "message" in changes:
        message = changes.get("message")
        if not isinstance(message, str):
            raise HTTPException(status_code=400, detail="message must be a string")
        normalized_message = message.strip()
        if not normalized_message:
            raise HTTPException(status_code=400, detail="message cannot be empty")
        notice.message = normalized_message

    if "type" in changes:
        notice.type = _normalize_notice_type(changes.get("type"))

    if "isActive" in changes:
        notice.is_active = bool(changes.get("isActive"))

    if "startsAt" in changes:
        notice.starts_at = _normalize_datetime(changes.get("startsAt"))

    if "endsAt" in changes:
        notice.ends_at = _normalize_datetime(changes.get("endsAt"))

    if "showAs" in changes:
        notice.show_as = _normalize_show_as(changes.get("showAs"))

    if "dismissible" in changes:
        notice.dismissible = bool(changes.get("dismissible"))

    _validate_notice_window(notice.starts_at, notice.ends_at)

    notice.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(notice)
    return serialize_notice(notice)


def delete_notice(db: Session, notice_id: int) -> None:
    notice = system_notices_repository.get_notice_by_id(db=db, notice_id=notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="System notice not found")
    system_notices_repository.delete_notice(db=db, notice=notice)
    db.commit()


def set_notice_active_status(
    db: Session,
    notice_id: int,
    is_active: bool,
) -> dict[str, Any]:
    notice = system_notices_repository.get_notice_by_id(db=db, notice_id=notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="System notice not found")

    notice.is_active = bool(is_active)
    notice.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(notice)
    return serialize_notice(notice)

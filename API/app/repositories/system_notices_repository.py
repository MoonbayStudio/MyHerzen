from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from backend.app.db.models import SystemNotice


def list_notices(db: Session) -> List[SystemNotice]:
    return db.query(SystemNotice).order_by(
        SystemNotice.created_at.desc(),
        SystemNotice.id.desc(),
    ).all()


def get_notice_by_id(db: Session, notice_id: int) -> Optional[SystemNotice]:
    return db.query(SystemNotice).filter(SystemNotice.id == notice_id).first()


def get_active_notice(db: Session) -> Optional[SystemNotice]:
    now = datetime.now(timezone.utc)
    severity_order = case(
        (SystemNotice.type == "critical", 0),
        (SystemNotice.type == "maintenance", 1),
        (SystemNotice.type == "warning", 2),
        else_=3,
    )
    return db.query(SystemNotice).filter(
        SystemNotice.is_active == True,
        or_(SystemNotice.starts_at.is_(None), SystemNotice.starts_at <= now),
        or_(SystemNotice.ends_at.is_(None), SystemNotice.ends_at >= now),
    ).order_by(
        severity_order.asc(),
        SystemNotice.updated_at.desc(),
        SystemNotice.id.desc(),
    ).first()


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
    now: datetime,
) -> SystemNotice:
    notice = SystemNotice(
        title=title,
        message=message,
        type=notice_type,
        is_active=is_active,
        starts_at=starts_at,
        ends_at=ends_at,
        show_as=show_as,
        dismissible=dismissible,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(notice)
    return notice


def delete_notice(db: Session, notice: SystemNotice) -> None:
    db.delete(notice)

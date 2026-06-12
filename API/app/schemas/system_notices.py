from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


NoticeType = Literal["info", "warning", "maintenance", "critical"]
NoticeShowAs = Literal["banner", "modal"]


class SystemNoticeCreateRequest(BaseModel):
    title: str
    message: str
    type: NoticeType = "info"
    isActive: bool = False
    startsAt: Optional[datetime] = None
    endsAt: Optional[datetime] = None
    showAs: NoticeShowAs = "banner"
    dismissible: bool = True


class SystemNoticeUpdateRequest(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[NoticeType] = None
    isActive: Optional[bool] = None
    startsAt: Optional[datetime] = None
    endsAt: Optional[datetime] = None
    showAs: Optional[NoticeShowAs] = None
    dismissible: Optional[bool] = None


class SystemNoticeResponse(BaseModel):
    id: int
    title: str
    message: str
    type: NoticeType
    isActive: bool
    startsAt: Optional[datetime] = None
    endsAt: Optional[datetime] = None
    showAs: NoticeShowAs
    dismissible: bool
    createdAt: datetime
    updatedAt: datetime
    createdBy: Optional[int] = None


class SystemNoticePublicItem(BaseModel):
    id: int
    title: str
    message: str
    type: NoticeType
    showAs: NoticeShowAs
    dismissible: bool
    startsAt: Optional[datetime] = None
    endsAt: Optional[datetime] = None


class ActiveSystemNoticeResponse(BaseModel):
    isActive: bool
    notice: Optional[SystemNoticePublicItem] = None

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


DevicePlatform = Literal["iOS", "macOS", "android", "web", "unknown"]


class SessionClientInfo(BaseModel):
    deviceId: Optional[str] = None
    deviceName: Optional[str] = None
    platform: Optional[DevicePlatform] = None
    appVersion: Optional[str] = None


class AccountSessionResponse(BaseModel):
    id: int
    deviceId: Optional[str] = None
    deviceName: Optional[str] = None
    platform: Optional[str] = None
    appVersion: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    createdAt: datetime
    lastSeenAt: datetime
    revokedAt: Optional[datetime] = None
    isCurrent: bool


class AdminUserSessionResponse(BaseModel):
    id: int
    userId: int
    deviceId: Optional[str] = None
    deviceName: Optional[str] = None
    platform: Optional[str] = None
    appVersion: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    createdAt: datetime
    lastSeenAt: datetime
    revokedAt: Optional[datetime] = None


class SessionRevokeResponse(BaseModel):
    success: bool
    revokedAt: datetime


class LogoutOthersResponse(BaseModel):
    success: bool
    revokedCount: int
    note: Optional[str] = None

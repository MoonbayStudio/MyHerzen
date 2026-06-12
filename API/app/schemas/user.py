from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from backend.app.schemas.sessions import SessionClientInfo

class SuccessResponse(BaseModel):
    success: bool

class UserRoleResponse(BaseModel):
    type: str
    title: str
    groupId: Optional[int] = None

class BadgeResponse(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    icon_name: str
    rarity: str

class PendingRoleRequestBadge(BaseModel):
    id: str
    requestedRole: str
    createdAt: datetime

class AppleUserResponse(BaseModel):
    id: str
    displayName: Optional[str] = None
    email: Optional[str] = None
    appleEmail: Optional[str] = None
    contactEmail: Optional[str] = None
    contactEmailVerified: bool = False
    pendingContactEmail: Optional[str] = None
    needsContactEmail: bool = False
    isAppleRelayEmail: bool = False
    roles: List[UserRoleResponse] = []
    badges: List[BadgeResponse] = []
    tier: str = "free"
    remainingToday: Optional[int] = None
    scheduleCacheWeeks: int = 2
    liveActivityEnabled: bool = True
    hasPassword: bool
    emailVerified: bool = False
    pendingEmail: Optional[str] = None
    linkedProviders: List[str] = []

class AppleLoginRequest(SessionClientInfo):
    identityToken: str
    authorizationCode: Optional[str] = None
    fullName: Optional[str] = None
    email: Optional[str] = None

class GoogleLoginRequest(SessionClientInfo):
    idToken: str
    systemVersion: Optional[str] = None

class AppleLoginResponse(BaseModel):
    token: str
    user: AppleUserResponse

class EmailChangeRequest(BaseModel):
    email: str

class EmailConfirmRequest(BaseModel):
    code: str

class UpdateNameRequest(BaseModel):
    name: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    displayName: str

class PasswordSetupRequest(BaseModel):
    password: str

class PasswordLoginRequest(SessionClientInfo):
    email: str
    password: str

class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str

class ResetPasswordRequest(BaseModel):
    email: str

class ResetPasswordConfirmRequest(BaseModel):
    code: str
    newPassword: str

class ContactEmailRequest(BaseModel):
    email: str

class SignupRequest(SessionClientInfo):
    email: str
    password: str
    displayName: str

class SignupVerifyRequest(SessionClientInfo):
    email: str
    code: str

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.schemas.user import UserRoleResponse, PendingRoleRequestBadge, BadgeResponse

class GrantRoleRequest(BaseModel):
    user_id: int
    role: str

class RevokeRoleRequest(BaseModel):
    user_id: int
    role: str

class GrantBadgeRequest(BaseModel):
    badge_code: str
    note: Optional[str] = None

class AdminUserResponse(BaseModel):
    id: str
    email: Optional[str]
    name: Optional[str]
    roles: List[UserRoleResponse]
    badges: List[BadgeResponse] = []
    remainingToday: int
    tier: str
    pendingRoleRequests: List[PendingRoleRequestBadge] = []

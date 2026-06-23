from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class GroupMembershipResponse(BaseModel):
    id: int
    group_id: int
    user_id: int
    role: str
    status: str
    invited_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class GroupInviteRequest(BaseModel):
    user_id: int
    role: str


class GroupChangeRequestCreate(BaseModel):
    requestedGroupId: int
    requestedGroupName: Optional[str] = None
    comment: Optional[str] = None


class GroupChangeRequestReview(BaseModel):
    comment: Optional[str] = None


class GroupChangeRequestResponse(BaseModel):
    id: int
    userId: int
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    currentGroupId: Optional[int] = None
    currentGroupName: Optional[str] = None
    requestedGroupId: int
    requestedGroupName: Optional[str] = None
    comment: Optional[str] = None
    status: str
    moderatorId: Optional[int] = None
    reviewedByAdminEmail: Optional[str] = None
    reviewComment: Optional[str] = None
    createdAt: datetime
    reviewedAt: Optional[datetime] = None

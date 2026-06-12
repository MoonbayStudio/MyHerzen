from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class MeRoleRequestCreateRequest(BaseModel):
    role: str
    message: Optional[str] = None

class MeRoleRequestResponse(BaseModel):
    id: str
    roleType: str
    requestedRole: str
    message: Optional[str] = None
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    status: str
    createdAt: datetime
    reviewedAt: Optional[datetime] = None
    reviewComment: Optional[str] = None

class AdminRoleRequestResponse(BaseModel):
    id: str
    userId: str
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    roleType: str
    requestedRole: str
    message: Optional[str] = None
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    status: str
    createdAt: datetime
    reviewedAt: Optional[datetime] = None
    reviewedByAdminEmail: Optional[str] = None
    reviewComment: Optional[str] = None

class RoleRequestReviewRequest(BaseModel):
    comment: Optional[str] = None

class LeaderRequestCreateRequest(BaseModel):
    groupId: int
    groupName: Optional[str] = None
    comment: Optional[str] = None

class LeaderRequestRejectRequest(BaseModel):
    comment: Optional[str] = None

class LeaderRequestResponse(BaseModel):
    id: int
    userId: int
    groupId: int
    groupName: Optional[str] = None
    status: str
    comment: Optional[str] = None
    moderatorId: Optional[int] = None
    createdAt: datetime
    reviewedAt: Optional[datetime] = None

class RoleRequestCreateRequest(BaseModel):
    roleType: str
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    comment: Optional[str] = None

class RoleRequestRejectRequest(BaseModel):
    comment: Optional[str] = None

class RoleRequestResponse(BaseModel):
    id: int
    userId: int
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    roleType: str
    requestedRole: str
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    message: Optional[str] = None
    comment: Optional[str] = None
    status: str
    moderatorId: Optional[int] = None
    createdAt: datetime
    reviewedAt: Optional[datetime] = None
    reviewedByAdminEmail: Optional[str] = None
    reviewComment: Optional[str] = None

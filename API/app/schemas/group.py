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

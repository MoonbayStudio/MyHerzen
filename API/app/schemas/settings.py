from typing import Optional
from pydantic import BaseModel

class UserSettingsRequest(BaseModel):
    selectedGroupId: Optional[int] = None
    selectedGroupName: Optional[str] = None
    scheduleCacheWeeks: Optional[int] = None
    liveActivityEnabled: Optional[bool] = None

class UserSettingsResponse(BaseModel):
    selectedGroupId: Optional[int] = None
    selectedGroupName: Optional[str] = None
    scheduleCacheWeeks: int
    liveActivityEnabled: bool

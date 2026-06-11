from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


SettingValueType = Literal["string", "int", "bool", "json"]


class AppSettingAdminResponse(BaseModel):
    key: str
    value: Any
    valueType: SettingValueType
    description: Optional[str] = None
    isPublic: bool
    updatedAt: Optional[datetime] = None
    updatedBy: Optional[int] = None


class UpdateAppSettingRequest(BaseModel):
    value: Any
    description: Optional[str] = None
    isPublic: Optional[bool] = None


class PublicConfigResponse(BaseModel):
    settings: Dict[str, Any]

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.permission import PermissionLevel


class HostPermissionCreate(BaseModel):
    host_id: int
    team_id: Optional[int] = None
    user_id: Optional[int] = None
    permission_level: PermissionLevel = PermissionLevel.read_execute
    can_upload: bool = False
    can_download: bool = False
    can_execute: bool = True
    allowed_time_start: Optional[str] = None
    allowed_time_end: Optional[str] = None
    allowed_days: Optional[str] = None


class HostPermissionUpdate(BaseModel):
    permission_level: Optional[PermissionLevel] = None
    can_upload: Optional[bool] = None
    can_download: Optional[bool] = None
    can_execute: Optional[bool] = None
    allowed_time_start: Optional[str] = None
    allowed_time_end: Optional[str] = None
    allowed_days: Optional[str] = None
    is_active: Optional[bool] = None


class HostPermissionResponse(BaseModel):
    id: int
    host_id: int
    team_id: Optional[int] = None
    user_id: Optional[int] = None
    permission_level: PermissionLevel
    can_upload: bool
    can_download: bool
    can_execute: bool
    allowed_time_start: Optional[str] = None
    allowed_time_end: Optional[str] = None
    allowed_days: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TemporaryPermissionCreate(BaseModel):
    host_id: int
    user_id: int
    permission_level: PermissionLevel = PermissionLevel.read_execute
    reason: Optional[str] = None
    expires_at: datetime


class TemporaryPermissionResponse(BaseModel):
    id: int
    host_id: int
    user_id: int
    granted_by: Optional[int] = None
    permission_level: PermissionLevel
    reason: Optional[str] = None
    expires_at: datetime
    is_revoked: bool
    created_at: datetime

    model_config = {"from_attributes": True}

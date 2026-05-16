from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.host import AuthType, HostStatus


class HostCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    hostname: str = Field(..., max_length=255)
    ip_address: str = Field(..., max_length=64)
    port: int = 22
    auth_type: AuthType = AuthType.password
    username: str = Field(..., max_length=128)
    password: Optional[str] = None
    private_key: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[int] = None
    group_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class HostUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    auth_type: Optional[AuthType] = None
    username: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[int] = None
    group_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class HostResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: str
    port: int
    auth_type: AuthType
    username: str
    status: HostStatus
    os_info: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[int] = None
    group_id: Optional[int] = None
    tags: Optional[List[dict]] = None
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HostBatchImport(BaseModel):
    hosts: List[HostCreate]


class ConnectivityTestResult(BaseModel):
    host_id: int
    success: bool
    message: str
    latency_ms: Optional[float] = None


class HostGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    parent_id: Optional[int] = None


class HostGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    host_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class HostTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str = "#1890ff"


class HostTagResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}

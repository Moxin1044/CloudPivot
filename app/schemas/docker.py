from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DockerHostCreate(BaseModel):
    name: str
    host: str
    host_id: Optional[int] = None
    team_id: Optional[int] = None
    tls_verify: bool = False
    cert_path: Optional[str] = None


class DockerHostResponse(BaseModel):
    id: int
    name: str
    host: str
    host_id: Optional[int] = None
    team_id: Optional[int] = None
    tls_verify: bool
    is_active: bool
    version_info: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContainerResponse(BaseModel):
    id: str
    name: Optional[str] = None
    image: Optional[str] = None
    status: Optional[str] = None
    state: Optional[str] = None
    ports: Optional[list] = None
    labels: Optional[dict] = None
    created: Optional[int] = None


class ContainerStatsResponse(BaseModel):
    cpu_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    memory_limit_mb: Optional[float] = None
    memory_percent: Optional[float] = None
    network_in_bytes: Optional[int] = None
    network_out_bytes: Optional[int] = None
    block_read_bytes: Optional[int] = None
    block_write_bytes: Optional[int] = None
    pids: Optional[int] = None


class ImageResponse(BaseModel):
    id: str
    repo_tags: Optional[List[str]] = None
    size_mb: Optional[float] = None
    created: Optional[int] = None


class ContainerLogResponse(BaseModel):
    logs: str


class ContainerActionRequest(BaseModel):
    timeout: int = 10


class ExecRequest(BaseModel):
    command: str
    tty: bool = True

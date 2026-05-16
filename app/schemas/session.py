from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.session import SessionStatus, RiskLevel


class SSHSessionResponse(BaseModel):
    id: int
    session_id: str
    user_id: Optional[int] = None
    host_id: Optional[int] = None
    client_ip: Optional[str] = None
    status: SessionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    username: Optional[str] = None
    host_name: Optional[str] = None

    model_config = {"from_attributes": True}


class SessionCommandResponse(BaseModel):
    id: int
    session_id: int
    command: str
    risk_level: RiskLevel
    is_blocked: bool
    output_snippet: Optional[str] = None
    executed_at: datetime

    model_config = {"from_attributes": True}


class SessionRecordingResponse(BaseModel):
    id: int
    session_id: int
    file_path: str
    file_size: Optional[int] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}

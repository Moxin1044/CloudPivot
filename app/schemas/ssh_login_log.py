from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SSHLoginLogResponse(BaseModel):
    id: int
    host_id: int
    host_name: Optional[str] = None
    username: Optional[str] = None
    login_ip: Optional[str] = None
    login_port: Optional[int] = None
    auth_method: Optional[str] = None
    is_success: bool
    fail_reason: Optional[str] = None
    login_at: datetime
    logout_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    risk_level: str
    is_new_ip: bool
    is_brute_force: bool
    geo_location: Optional[str] = None

    model_config = {"from_attributes": True}


class SSHLoginAnalysisSummary(BaseModel):
    total_logins: int
    failed_logins: int
    unique_ips: int
    unique_users: int
    brute_force_attempts: int
    new_ip_logins: int
    top_source_ips: list[dict]
    top_users: list[dict]
    hourly_trend: list[dict]
    risk_distribution: list[dict]

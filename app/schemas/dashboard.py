from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DashboardOverview(BaseModel):
    total_hosts: int = 0
    online_hosts: int = 0
    offline_hosts: int = 0
    active_sessions: int = 0
    total_users: int = 0
    active_alerts: int = 0
    risk_commands_today: int = 0


class ResourceUsage(BaseModel):
    host_id: int
    host_name: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None


class RecentAudit(BaseModel):
    session_id: str
    username: Optional[str] = None
    host_name: Optional[str] = None
    command: str
    risk_level: str
    executed_at: datetime


class RecentAlert(BaseModel):
    id: int
    title: str
    severity: str
    host_name: Optional[str] = None
    created_at: datetime


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    resource_usage: List[ResourceUsage] = []
    recent_audits: List[RecentAudit] = []
    recent_alerts: List[RecentAlert] = []

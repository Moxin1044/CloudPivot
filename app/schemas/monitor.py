from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.monitor import AlertSeverity, AlertStatus


class HostMetricResponse(BaseModel):
    id: int
    host_id: int
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_gb: Optional[float] = None
    memory_total_gb: Optional[float] = None
    disk_percent: Optional[float] = None
    disk_used_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None
    network_in_mbps: Optional[float] = None
    network_out_mbps: Optional[float] = None
    load_1min: Optional[float] = None
    load_5min: Optional[float] = None
    load_15min: Optional[float] = None
    collected_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metric_type: str
    condition: str
    threshold: float
    duration_seconds: int = 0
    severity: AlertSeverity = AlertSeverity.warning
    host_id: Optional[int] = None
    team_id: Optional[int] = None
    notify_channels: Optional[list] = None
    webhook_url: Optional[str] = None
    is_enabled: bool = True


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    metric_type: str
    condition: str
    threshold: float
    duration_seconds: int
    severity: AlertSeverity
    host_id: Optional[int] = None
    team_id: Optional[int] = None
    notify_channels: Optional[list] = None
    webhook_url: Optional[str] = None
    is_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRecordResponse(BaseModel):
    id: int
    rule_id: Optional[int] = None
    host_id: Optional[int] = None
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: Optional[str] = None
    notified_channels: Optional[list] = None
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

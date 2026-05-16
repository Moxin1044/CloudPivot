from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
import enum


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    pending = "pending"
    acknowledged = "acknowledged"
    resolved = "resolved"


class HostMetric(Base):
    __tablename__ = "host_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True)
    cpu_percent = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    memory_used_gb = Column(Float, nullable=True)
    memory_total_gb = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_used_gb = Column(Float, nullable=True)
    disk_total_gb = Column(Float, nullable=True)
    network_in_mbps = Column(Float, nullable=True)
    network_out_mbps = Column(Float, nullable=True)
    load_1min = Column(Float, nullable=True)
    load_5min = Column(Float, nullable=True)
    load_15min = Column(Float, nullable=True)
    extra_data = Column(JSON, nullable=True)
    collected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    host = relationship("Host", back_populates="metrics", foreign_keys=[host_id])


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    metric_type = Column(String(64), nullable=False)  # cpu, memory, disk, network, custom
    condition = Column(String(32), nullable=False)     # gt, lt, gte, lte, eq
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=0)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.warning, nullable=False)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    notify_channels = Column(JSON, nullable=True)  # ["email", "webhook", "feishu", "dingtalk"]
    webhook_url = Column(String(512), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True, index=True)
    severity = Column(SAEnum(AlertSeverity), nullable=False)
    status = Column(SAEnum(AlertStatus), default=AlertStatus.pending, nullable=False)
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=True)
    notified_channels = Column(JSON, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

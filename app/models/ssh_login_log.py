from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class SSHLoginLog(Base):
    """SSH登录到主机的日志记录（从目标主机采集）"""
    __tablename__ = "ssh_login_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(64), nullable=True, index=True)
    login_ip = Column(String(64), nullable=True, index=True)
    login_port = Column(Integer, nullable=True)
    auth_method = Column(String(32), nullable=True)  # password, publickey, keyboard-interactive
    is_success = Column(Boolean, default=True, nullable=False)
    fail_reason = Column(String(256), nullable=True)
    login_at = Column(DateTime(timezone=True), nullable=False, index=True)
    logout_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    raw_log = Column(Text, nullable=True)

    # 分析字段
    is_analyzed = Column(Boolean, default=False, nullable=False)
    risk_level = Column(String(16), default="safe", nullable=False)  # safe, warning, danger
    geo_location = Column(String(128), nullable=True)
    is_new_ip = Column(Boolean, default=False, nullable=False)
    is_brute_force = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    host = relationship("Host", back_populates="ssh_login_logs")

    __table_args__ = (
        Index("ix_ssh_login_logs_host_login_at", "host_id", "login_at"),
        Index("ix_ssh_login_logs_ip_login_at", "login_ip", "login_at"),
    )

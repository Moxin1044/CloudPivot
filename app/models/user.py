from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    locked = "locked"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(128), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.viewer, nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.active, nullable=False)
    mfa_secret = Column(String(64), nullable=True)
    language = Column(String(10), default="zh-CN", nullable=False)
    theme = Column(String(10), default="light", nullable=False)
    # Personal notification settings
    notification_email = Column(String(255), nullable=True)
    feishu_webhook = Column(String(512), nullable=True)
    dingtalk_webhook = Column(String(512), nullable=True)
    notify_channels = Column(String(128), nullable=True)  # comma-separated: "email,feishu,dingtalk"
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(64), nullable=True)
    token_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    team_memberships = relationship("TeamMember", back_populates="user", foreign_keys="TeamMember.user_id")
    login_logs = relationship("LoginLog", back_populates="user", foreign_keys="LoginLog.user_id")
    ssh_sessions = relationship("SSHSession", back_populates="user", foreign_keys="SSHSession.user_id")

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.active

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

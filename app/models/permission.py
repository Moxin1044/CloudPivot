from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
import enum


class PermissionLevel(str, enum.Enum):
    readonly = "readonly"
    read_execute = "read_execute"
    read_execute_upload = "read_execute_upload"
    full = "full"


class HostPermission(Base):
    __tablename__ = "host_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    permission_level = Column(SAEnum(PermissionLevel), default=PermissionLevel.read_execute, nullable=False)
    can_upload = Column(Boolean, default=False, nullable=False)
    can_download = Column(Boolean, default=False, nullable=False)
    can_execute = Column(Boolean, default=True, nullable=False)
    allowed_time_start = Column(String(5), nullable=True)  # HH:MM
    allowed_time_end = Column(String(5), nullable=True)    # HH:MM
    allowed_days = Column(String(64), nullable=True)       # e.g. "1,2,3,4,5" for Mon-Fri
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    host = relationship("Host", back_populates="permissions", foreign_keys=[host_id])
    team = relationship("Team", back_populates="permissions", foreign_keys=[team_id])


class TemporaryPermission(Base):
    __tablename__ = "temporary_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    permission_level = Column(SAEnum(PermissionLevel), default=PermissionLevel.read_execute, nullable=False)
    reason = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

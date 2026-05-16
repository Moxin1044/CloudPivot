from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
import enum


class SessionStatus(str, enum.Enum):
    active = "active"
    closed = "closed"
    terminated = "terminated"


class RiskLevel(str, enum.Enum):
    safe = "safe"
    warning = "warning"
    danger = "danger"


class SSHSession(Base):
    __tablename__ = "ssh_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True, index=True)
    client_ip = Column(String(64), nullable=True)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.active, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="ssh_sessions", foreign_keys=[user_id])
    host = relationship("Host", back_populates="ssh_sessions", foreign_keys=[host_id])
    commands = relationship("SessionCommand", back_populates="session", foreign_keys="SessionCommand.session_id")
    recording = relationship("SessionRecording", back_populates="session", uselist=False, foreign_keys="SessionRecording.session_id")


class SessionCommand(Base):
    __tablename__ = "session_commands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("ssh_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    command = Column(Text, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.safe, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    output_snippet = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("SSHSession", back_populates="commands", foreign_keys=[session_id])


class SessionRecording(Base):
    __tablename__ = "session_recordings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("ssh_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("SSHSession", back_populates="recording", foreign_keys=[session_id])

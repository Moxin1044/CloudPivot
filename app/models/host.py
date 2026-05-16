from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
import enum


class AuthType(str, enum.Enum):
    password = "password"
    key = "key"


class HostStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    unknown = "unknown"


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(64), nullable=False, index=True)
    port = Column(Integer, default=22, nullable=False)
    auth_type = Column(SAEnum(AuthType), default=AuthType.password, nullable=False)
    username = Column(String(128), nullable=False)
    password_encrypted = Column(Text, nullable=True)
    private_key_encrypted = Column(Text, nullable=True)
    status = Column(SAEnum(HostStatus), default=HostStatus.unknown, nullable=False)
    os_info = Column(String(255), nullable=True)
    os_name = Column(String(64), nullable=True)
    os_version = Column(String(64), nullable=True)
    public_ip = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("host_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship("Team", back_populates="hosts", foreign_keys=[team_id])
    group = relationship("HostGroup", back_populates="hosts", foreign_keys=[group_id])
    tags = relationship("HostTag", secondary="host_tag_associations", back_populates="hosts")
    permissions = relationship("HostPermission", back_populates="host", foreign_keys="HostPermission.host_id")
    ssh_sessions = relationship("SSHSession", back_populates="host", foreign_keys="SSHSession.host_id")
    metrics = relationship("HostMetric", back_populates="host", foreign_keys="HostMetric.host_id")


class HostGroup(Base):
    __tablename__ = "host_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("host_groups.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    hosts = relationship("Host", back_populates="group", foreign_keys="Host.group_id")
    children = relationship("HostGroup", backref="parent", remote_side="HostGroup.id", foreign_keys="HostGroup.parent_id")


class HostTag(Base):
    __tablename__ = "host_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    color = Column(String(16), nullable=True, default="#1890ff")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    hosts = relationship("Host", secondary="host_tag_associations", back_populates="tags")


# Association table for host-tag many-to-many
from sqlalchemy import Table, MetaData
metadata = Base.metadata

host_tag_association = Table(
    "host_tag_associations",
    metadata,
    Column("host_id", Integer, ForeignKey("hosts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("host_tags.id", ondelete="CASCADE"), primary_key=True),
)

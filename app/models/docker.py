from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class DockerHost(Base):
    __tablename__ = "docker_hosts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    host = Column(String(512), nullable=False)  # docker socket or tcp address
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    tls_verify = Column(Boolean, default=False)
    cert_path = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    version_info = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    containers = relationship("ContainerInfo", back_populates="docker_host", foreign_keys="ContainerInfo.docker_host_id")


class ContainerInfo(Base):
    __tablename__ = "container_infos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    docker_host_id = Column(Integer, ForeignKey("docker_hosts.id", ondelete="CASCADE"), nullable=False, index=True)
    container_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=True)
    image = Column(String(256), nullable=True)
    status = Column(String(64), nullable=True)
    state = Column(String(32), nullable=True)
    ports = Column(JSON, nullable=True)
    labels = Column(JSON, nullable=True)
    network_mode = Column(String(64), nullable=True)
    created_at_docker = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    docker_host = relationship("DockerHost", back_populates="containers", foreign_keys=[docker_host_id])

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime, timezone
from app.database import Base


class SiteConfig(Base):
    __tablename__ = "site_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(512), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

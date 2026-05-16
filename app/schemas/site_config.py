from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SiteConfigItem(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class SiteConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None


class SiteConfigResponse(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RegistrationStatusResponse(BaseModel):
    allow_register: bool = True

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.team import TeamRole


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberAdd(BaseModel):
    user_id: int
    role: TeamRole = TeamRole.viewer


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    role: TeamRole
    joined_at: datetime
    username: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole, UserStatus


# ===== Auth =====
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ===== User =====
class UserBase(BaseModel):
    username: str
    email: str
    display_name: Optional[str] = None
    role: UserRole = UserRole.viewer
    status: UserStatus = UserStatus.active
    language: str = "zh-CN"
    theme: str = "light"


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class UserNotificationUpdate(BaseModel):
    notification_email: Optional[str] = None
    feishu_webhook: Optional[str] = None
    dingtalk_webhook: Optional[str] = None
    notify_channels: Optional[str] = None  # comma-separated: "email,feishu,dingtalk"


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    notification_email: Optional[str] = None
    feishu_webhook: Optional[str] = None
    dingtalk_webhook: Optional[str] = None
    notify_channels: Optional[str] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.log import LoginLog
from app.models.site_config import SiteConfig
from app.schemas.user import (
    LoginRequest, RegisterRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, UserCreate,
    UserUpdate, ChangePasswordRequest, UserNotificationUpdate,
)
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token,
    blacklist_token, is_token_blacklisted,
    check_login_attempts, record_login_attempt,
)
from app.routers.captcha import verify_captcha
from app.dependencies import get_current_user, get_current_active_admin
from app.config import settings
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SiteConfig).where(SiteConfig.key == "allow_register"))
    config = result.scalar_one_or_none()
    if config and config.value == "false":
        raise HTTPException(status_code=403, detail="Registration is currently disabled")

    result = await db.execute(
        select(User).where(or_(User.username == data.username, User.email == data.email))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        display_name=data.display_name or data.username,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"

    # Check login attempt limit (by username + IP)
    attempt_key = f"{data.username}:{ip}"
    if not check_login_attempts(attempt_key):
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Please try again in {settings.LOGIN_LOCKOUT_MINUTES} minutes.",
        )

    # Verify captcha
    if settings.CAPTCHA_ENABLED:
        if not verify_captcha(data.captcha_id or "", data.captcha_code or ""):
            record_login_attempt(attempt_key, False)
            raise HTTPException(status_code=400, detail="Invalid captcha")

    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    login_log = LoginLog(
        username=data.username,
        login_ip=ip,
        user_agent=request.headers.get("user-agent"),
        login_method="password",
    )

    if not user or not verify_password(data.password, user.hashed_password):
        login_log.is_success = False
        login_log.fail_reason = "Invalid credentials"
        db.add(login_log)
        await db.commit()
        record_login_attempt(attempt_key, False)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        login_log.is_success = False
        login_log.fail_reason = "Account disabled"
        db.add(login_log)
        await db.commit()
        record_login_attempt(attempt_key, False)
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Update login info
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = ip

    login_log.user_id = user.id
    login_log.is_success = True
    db.add(login_log)
    await db.commit()

    record_login_attempt(attempt_key, True)
    tv = user.token_version if hasattr(user, "token_version") else 1

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value}, token_version=tv
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id)}, token_version=tv
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    if is_token_blacklisted(data.refresh_token):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Check token version matches current user version
    token_ver = payload.get("ver", 1)
    user_ver = user.token_version if hasattr(user, "token_version") else 1
    if token_ver != user_ver:
        raise HTTPException(status_code=401, detail="Token version mismatch, please re-login")

    # Blacklist old refresh token (rotation)
    old_exp = payload.get("exp", 0)
    remaining = max(old_exp - int(datetime.now(timezone.utc).timestamp()), 0)
    if remaining > 0:
        blacklist_token(data.refresh_token, ttl_seconds=remaining)

    tv = user.token_version if hasattr(user, "token_version") else 1
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value}, token_version=tv
    )
    refresh_token_new = create_refresh_token({"sub": str(user.id)}, token_version=tv)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_new,
        expires_in=settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Logout and blacklist the current access token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    if token:
        blacklist_token(token)
    return {"message": "Logged out successfully"}


# ===== User Management =====
user_router = APIRouter(prefix="/users", tags=["User Management"])


@user_router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@user_router.put("/me", response_model=UserResponse, summary="更新当前用户信息")
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.language is not None:
        current_user.language = data.language
    if data.theme is not None:
        current_user.theme = data.theme
    if data.display_name is not None:
        current_user.display_name = data.display_name
    if data.email is not None:
        current_user.email = data.email
    await db.flush()
    await db.refresh(current_user)
    return current_user


@user_router.put("/me/notifications", response_model=UserResponse, summary="更新个人通知配置")
async def update_my_notifications(
    data: UserNotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@user_router.put("/me/password", summary="修改密码")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    current_user.hashed_password = hash_password(data.new_password)
    # Increment token version to invalidate all existing tokens
    current_user.token_version = (current_user.token_version or 1) + 1
    await db.flush()
    return {"message": "Password changed successfully"}


@user_router.get("", response_model=list[UserResponse], summary="获取用户列表")
async def list_users(
    skip: int = 0,
    limit: int = 20,
    role: str = None,
    status: str = None,
    search: str = None,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.display_name.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@user_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="创建用户")
async def create_user(
    data: UserCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(or_(User.username == data.username, User.email == data.email))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        display_name=data.display_name or data.username,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@user_router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@user_router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "password" and value:
            user.hashed_password = hash_password(value)
        elif hasattr(user, field):
            setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user


@user_router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.delete(user)
    return {"message": "User deleted"}

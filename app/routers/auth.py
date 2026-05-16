from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.log import LoginLog
from app.schemas.user import (
    LoginRequest, RegisterRequest, TokenResponse,
    RefreshTokenRequest, UserResponse, UserCreate,
    UserUpdate, ChangePasswordRequest, UserNotificationUpdate,
)
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token,
)
from app.dependencies import get_current_user, get_current_active_admin
from app.config import settings
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
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
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    login_log = LoginLog(
        username=data.username,
        login_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        login_method="password",
    )

    if not user or not verify_password(data.password, user.hashed_password):
        login_log.is_success = False
        login_log.fail_reason = "Invalid credentials"
        db.add(login_log)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        login_log.is_success = False
        login_log.fail_reason = "Account disabled"
        db.add(login_log)
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Update login info
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = request.client.host if request.client else None

    login_log.user_id = user.id
    login_log.is_success = True
    db.add(login_log)

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.APP_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


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
    await db.flush()
    return {"message": "Password changed successfully"}


@user_router.get("", response_model=list[UserResponse], summary="获取用户列表")
async def list_users(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).offset(skip).limit(limit))
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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models.permission import HostPermission, TemporaryPermission, PermissionLevel
from app.models.host import Host
from app.models.user import User
from app.schemas.permission import (
    HostPermissionCreate, HostPermissionUpdate, HostPermissionResponse,
    TemporaryPermissionCreate, TemporaryPermissionResponse,
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("", response_model=list[HostPermissionResponse], summary="获取权限列表")
async def list_permissions(
    host_id: int = None,
    team_id: int = None,
    user_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(HostPermission)
    if host_id:
        query = query.where(HostPermission.host_id == host_id)
    if team_id:
        query = query.where(HostPermission.team_id == team_id)
    if user_id:
        query = query.where(HostPermission.user_id == user_id)
    if not current_user.is_admin:
        from app.models.team import TeamMember
        query = query.join(
            TeamMember, TeamMember.team_id == HostPermission.team_id
        ).where(TeamMember.user_id == current_user.id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=HostPermissionResponse, status_code=status.HTTP_201_CREATED, summary="创建权限")
async def create_permission(
    data: HostPermissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not data.team_id and not data.user_id:
        raise HTTPException(status_code=400, detail="Must specify team_id or user_id")

    # Check host exists
    host_result = await db.execute(select(Host).where(Host.id == data.host_id))
    if not host_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Host not found")

    perm = HostPermission(**data.model_dump())
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm


@router.put("/{perm_id}", response_model=HostPermissionResponse, summary="更新权限")
async def update_permission(
    perm_id: int,
    data: HostPermissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HostPermission).where(HostPermission.id == perm_id))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(perm, field, value)
    await db.flush()
    await db.refresh(perm)
    return perm


@router.delete("/{perm_id}", summary="删除权限")
async def delete_permission(
    perm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HostPermission).where(HostPermission.id == perm_id))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    await db.delete(perm)
    return {"message": "Permission deleted"}


# ===== Temporary Permissions =====
@router.get("/temporary", response_model=list[TemporaryPermissionResponse], summary="获取临时授权列表")
async def list_temporary_permissions(
    user_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TemporaryPermission).where(TemporaryPermission.is_revoked == False)
    if user_id:
        query = query.where(TemporaryPermission.user_id == user_id)
    # Filter expired
    query = query.where(TemporaryPermission.expires_at > datetime.now(timezone.utc))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/temporary", response_model=TemporaryPermissionResponse, status_code=status.HTTP_201_CREATED, summary="创建临时授权")
async def create_temporary_permission(
    data: TemporaryPermissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Expires time must be in the future")

    perm = TemporaryPermission(
        host_id=data.host_id,
        user_id=data.user_id,
        granted_by=current_user.id,
        permission_level=data.permission_level,
        reason=data.reason,
        expires_at=data.expires_at,
    )
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm


@router.post("/temporary/{perm_id}/revoke", summary="撤销临时授权")
async def revoke_temporary_permission(
    perm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TemporaryPermission).where(TemporaryPermission.id == perm_id)
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Temporary permission not found")
    perm.is_revoked = True
    await db.flush()
    return {"message": "Temporary permission revoked"}

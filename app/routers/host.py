from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from app.database import get_db
from app.models.host import Host, HostGroup, HostTag, AuthType, HostStatus, host_tag_association
from app.models.user import User
from app.schemas.host import (
    HostCreate, HostUpdate, HostResponse,
    HostBatchImport, ConnectivityTestResult,
    HostGroupCreate, HostGroupResponse,
    HostTagCreate, HostTagResponse,
)
from app.dependencies import get_current_user, get_current_active_admin
from app.core.ssh import test_ssh_connectivity
from app.core.security import hash_password
import time

router = APIRouter(prefix="/hosts", tags=["Hosts"])


@router.get("", response_model=list[HostResponse], summary="获取主机列表")
async def list_hosts(
    skip: int = 0,
    limit: int = 20,
    group_id: Optional[int] = None,
    status: Optional[HostStatus] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Host).options(selectinload(Host.tags))
    if group_id is not None:
        query = query.where(Host.group_id == group_id)
    if status is not None:
        query = query.where(Host.status == status)
    if keyword:
        query = query.where(
            (Host.name.ilike(f"%{keyword}%")) |
            (Host.ip_address.ilike(f"%{keyword}%")) |
            (Host.hostname.ilike(f"%{keyword}%"))
        )
    # Non-admin users only see hosts in their teams
    if not current_user.is_admin:
        from app.models.team import TeamMember
        from app.models.permission import HostPermission
        query = query.join(
            HostPermission, HostPermission.host_id == Host.id
        ).join(
            TeamMember, TeamMember.team_id == HostPermission.team_id
        ).where(
            TeamMember.user_id == current_user.id,
            HostPermission.is_active == True,
        )

    result = await db.execute(query.offset(skip).limit(limit))
    hosts = result.scalars().all()

    # Tags already eager-loaded; build response manually to include tag dicts
    response = []
    for host in hosts:
        host_dict = HostResponse.model_validate(host).model_dump()
        host_dict["tags"] = [{"id": t.id, "name": t.name, "color": t.color} for t in host.tags]
        response.append(host_dict)
    return response


@router.post("", response_model=HostResponse, status_code=status.HTTP_201_CREATED, summary="添加主机")
async def create_host(
    data: HostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    host = Host(
        name=data.name,
        hostname=data.hostname,
        ip_address=data.ip_address,
        port=data.port,
        auth_type=data.auth_type,
        username=data.username,
        password_encrypted=data.password,
        private_key_encrypted=data.private_key,
        description=data.description,
        team_id=data.team_id,
        group_id=data.group_id,
    )
    db.add(host)
    await db.flush()
    await db.refresh(host)

    if data.tag_ids:
        for tag_id in data.tag_ids:
            await db.execute(
                host_tag_association.insert().values(host_id=host.id, tag_id=tag_id)
            )

    # Eager load tags for response serialization
    result = await db.execute(
        select(Host).options(selectinload(Host.tags)).where(Host.id == host.id)
    )
    host = result.scalar_one()
    return host


@router.post("/batch-import", summary="批量导入主机")
async def batch_import_hosts(
    data: HostBatchImport,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    created = []
    for host_data in data.hosts:
        host = Host(
            name=host_data.name,
            hostname=host_data.hostname,
            ip_address=host_data.ip_address,
            port=host_data.port,
            auth_type=host_data.auth_type,
            username=host_data.username,
            password_encrypted=host_data.password,
            private_key_encrypted=host_data.private_key,
            description=host_data.description,
            team_id=host_data.team_id,
            group_id=host_data.group_id,
        )
        db.add(host)
        created.append(host.name)
    await db.flush()
    return {"message": f"Imported {len(created)} hosts", "hosts": created}


@router.get("/{host_id}", response_model=HostResponse, summary="获取主机详情")
async def get_host(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Host).options(selectinload(Host.tags)).where(Host.id == host_id)
    )
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.put("/{host_id}", response_model=HostResponse, summary="更新主机")
async def update_host(
    host_id: int,
    data: HostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Host).options(selectinload(Host.tags)).where(Host.id == host_id)
    )
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    for field, value in data.model_dump(exclude_unset=True, exclude={"tag_ids"}).items():
        if field == "password" and value:
            setattr(host, "password_encrypted", value)
        elif field == "private_key" and value:
            setattr(host, "private_key_encrypted", value)
        elif hasattr(host, field):
            setattr(host, field, value)

    if data.tag_ids is not None:
        await db.execute(
            host_tag_association.delete().where(host_tag_association.c.host_id == host_id)
        )
        for tag_id in data.tag_ids:
            await db.execute(
                host_tag_association.insert().values(host_id=host_id, tag_id=tag_id)
            )

    await db.flush()
    await db.refresh(host)
    return host


@router.delete("/{host_id}", summary="删除主机")
async def delete_host(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    await db.delete(host)
    return {"message": "Host deleted"}


@router.post("/{host_id}/test", response_model=ConnectivityTestResult, summary="连通性检测")
async def test_connectivity(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    start_time = time.time()
    success, message = await test_ssh_connectivity(
        host=host.ip_address,
        port=host.port,
        username=host.username,
        password=host.password_encrypted,
        private_key=host.private_key_encrypted,
    )
    latency = (time.time() - start_time) * 1000

    # Update host status
    host.status = HostStatus.online if success else HostStatus.offline
    if success:
        host.last_connected_at = func.now()
    await db.flush()

    return ConnectivityTestResult(
        host_id=host_id,
        success=success,
        message=message,
        latency_ms=round(latency, 2) if success else None,
    )


# ===== Host Groups =====
@router.get("/groups/list", response_model=list[HostGroupResponse], summary="获取主机组列表")
async def list_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HostGroup))
    groups = result.scalars().all()
    response = []
    for g in groups:
        count_result = await db.execute(
            select(func.count(Host.id)).where(Host.group_id == g.id)
        )
        host_count = count_result.scalar() or 0
        group_dict = HostGroupResponse.model_validate(g).model_dump()
        group_dict["host_count"] = host_count
        response.append(group_dict)
    return response


@router.post("/groups", response_model=HostGroupResponse, status_code=status.HTTP_201_CREATED, summary="创建主机组")
async def create_group(
    data: HostGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = HostGroup(name=data.name, description=data.description, parent_id=data.parent_id)
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return group


# ===== Host Tags =====
@router.get("/tags/list", response_model=list[HostTagResponse], summary="获取标签列表")
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HostTag))
    return result.scalars().all()


@router.post("/tags", response_model=HostTagResponse, status_code=status.HTTP_201_CREATED, summary="创建标签")
async def create_tag(
    data: HostTagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tag = HostTag(name=data.name, color=data.color)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag

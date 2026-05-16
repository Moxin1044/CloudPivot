from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timedelta, timezone as tz
from app.database import get_db
from app.models.host import Host, HostGroup, HostTag, AuthType, HostStatus, host_tag_association
from app.models.monitor import HostMetric
from app.models.user import User
from app.schemas.host import (
    HostCreate, HostUpdate, HostResponse,
    HostBatchImport, ConnectivityTestResult,
    HostGroupCreate, HostGroupResponse,
    HostTagCreate, HostTagResponse,
)
from app.dependencies import get_current_user, get_current_active_admin
from app.core.ssh import test_ssh_connectivity, ssh_pool
from app.core.security import hash_password
import time
import re

router = APIRouter(prefix="/hosts", tags=["Hosts"])


@router.get("", response_model=dict, summary="获取主机列表")
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
            (Host.hostname.ilike(f"%{keyword}%")) |
            (Host.os_name.ilike(f"%{keyword}%")) |
            (Host.public_ip.ilike(f"%{keyword}%"))
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

    # Count without options to avoid subquery issues
    count_query = select(func.count()).select_from(Host)
    if group_id is not None:
        count_query = count_query.where(Host.group_id == group_id)
    if status is not None:
        count_query = count_query.where(Host.status == status)
    if keyword:
        count_query = count_query.where(
            (Host.name.ilike(f"%{keyword}%")) |
            (Host.ip_address.ilike(f"%{keyword}%")) |
            (Host.hostname.ilike(f"%{keyword}%")) |
            (Host.os_name.ilike(f"%{keyword}%")) |
            (Host.public_ip.ilike(f"%{keyword}%"))
        )
    if not current_user.is_admin:
        count_query = count_query.join(
            HostPermission, HostPermission.host_id == Host.id
        ).join(
            TeamMember, TeamMember.team_id == HostPermission.team_id
        ).where(
            TeamMember.user_id == current_user.id,
            HostPermission.is_active == True,
        )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    hosts = result.scalars().all()

    # Tags already eager-loaded; build response manually to include tag dicts
    items = []
    for host in hosts:
        host_dict = HostResponse.model_validate(host).model_dump()
        host_dict["tags"] = [{"id": t.id, "name": t.name, "color": t.color} for t in host.tags]
        items.append(host_dict)
    return {"total": total, "items": items}


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


@router.get("/{host_id}/metrics", summary="获取主机监控数据")
async def get_host_metrics_chart(
    host_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(tz.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(HostMetric)
        .where(HostMetric.host_id == host_id, HostMetric.collected_at >= since)
        .order_by(HostMetric.collected_at)
    )
    metrics = result.scalars().all()
    return [
        {
            "collected_at": m.collected_at.isoformat() if m.collected_at else None,
            "cpu_percent": m.cpu_percent,
            "memory_percent": m.memory_percent,
            "disk_percent": m.disk_percent,
            "network_in_kbps": m.network_in_kbps,
            "network_out_kbps": m.network_out_kbps,
            "load_1min": m.load_1min,
        }
        for m in metrics
    ]


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


async def _fetch_host_info(host: Host) -> dict:
    """SSH连接到主机并获取系统信息（公网IP、OS名称、版本）"""
    info = {"public_ip": None, "os_name": None, "os_version": None, "os_info": None}
    try:
        conn = await ssh_pool.get_connection(
            host=host.ip_address,
            port=host.port,
            username=host.username,
            password=host.password_encrypted or None,
            private_key=host.private_key_encrypted or None,
            timeout=15,
        )
    except Exception:
        return info

    def _is_valid_ip(ip: str) -> bool:
        if not ip:
            return False
        # IPv4
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
            return True
        # IPv6 (简判)
        if ":" in ip and re.match(r"^[0-9a-fA-F:]+$", ip):
            return True
        return False

    try:
        # 获取公网IP — 多途径尝试
        pub_ip = None
        # 方法1: curl
        if not pub_ip:
            try:
                pub_res = await conn.run(
                    "(curl -s --max-time 5 https://api.ipify.org 2>/dev/null) || "
                    "(curl -s --max-time 5 https://ifconfig.me 2>/dev/null) || "
                    "(curl -s --max-time 5 https://icanhazip.com 2>/dev/null) || echo ''",
                    check=False
                )
                candidate = pub_res.stdout.strip().splitlines()[0] if pub_res.stdout else ""
                if _is_valid_ip(candidate):
                    pub_ip = candidate
            except Exception:
                pass

        # 方法2: wget
        if not pub_ip:
            try:
                pub_res = await conn.run(
                    "(wget -qO- --timeout=5 https://api.ipify.org 2>/dev/null) || "
                    "(wget -qO- --timeout=5 https://ifconfig.me 2>/dev/null) || echo ''",
                    check=False
                )
                candidate = pub_res.stdout.strip().splitlines()[0] if pub_res.stdout else ""
                if _is_valid_ip(candidate):
                    pub_ip = candidate
            except Exception:
                pass

        # 方法3: 通过外部DNS获取（部分内网主机可能有UDP 53出网）
        if not pub_ip:
            try:
                pub_res = await conn.run(
                    "dig +short myip.opendns.com @resolver1.opendns.com 2>/dev/null || nslookup myip.opendns.com resolver1.opendns.com 2>/dev/null | tail -n2 | head -n1 | awk '{print $2}' || echo ''",
                    check=False
                )
                candidate = pub_res.stdout.strip().splitlines()[0] if pub_res.stdout else ""
                if _is_valid_ip(candidate):
                    pub_ip = candidate
            except Exception:
                pass

        if pub_ip:
            info["public_ip"] = pub_ip

        # 获取OS信息
        try:
            os_res = await conn.run("cat /etc/os-release 2>/dev/null || echo ''", check=False)
            os_text = os_res.stdout or ""
            os_name = None
            os_version = None
            for line in os_text.splitlines():
                if line.startswith("ID="):
                    os_name = line.split("=", 1)[1].strip().strip('"').title()
                elif line.startswith("VERSION_ID="):
                    os_version = line.split("=", 1)[1].strip().strip('"')
            if os_name:
                info["os_name"] = os_name
            if os_version:
                info["os_version"] = os_version
            if os_name and os_version:
                info["os_info"] = f"{os_name} {os_version}"
        except Exception:
            pass

        # fallback: uname
        if not info["os_name"]:
            try:
                uname_res = await conn.run("uname -s 2>/dev/null || echo ''", check=False)
                os_name = uname_res.stdout.strip()
                if os_name:
                    info["os_name"] = os_name
            except Exception:
                pass
        if not info["os_version"]:
            try:
                uname_r = await conn.run("uname -r 2>/dev/null || echo ''", check=False)
                os_version = uname_r.stdout.strip()
                if os_version:
                    info["os_version"] = os_version
            except Exception:
                pass
    except Exception:
        pass
    finally:
        await ssh_pool.release_connection(host.ip_address, host.port, host.username)
    return info


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
        # 连接成功时自动获取主机信息
        try:
            info = await _fetch_host_info(host)
            if info.get("public_ip"):
                host.public_ip = info["public_ip"]
            if info.get("os_name"):
                host.os_name = info["os_name"]
            if info.get("os_version"):
                host.os_version = info["os_version"]
            if info.get("os_info"):
                host.os_info = info["os_info"]
        except Exception:
            pass
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

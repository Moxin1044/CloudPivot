from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, cast, String
from app.database import get_db
from app.models.session import SSHSession, SessionCommand, SessionStatus, RiskLevel
from app.models.log import LoginLog, OperationLog
from app.models.user import User
from app.models.ssh_login_log import SSHLoginLog
from app.models.host import Host
from app.models.permission import HostPermission, TemporaryPermission
from app.models.team import TeamMember
from app.schemas.ssh_login_log import SSHLoginAnalysisSummary
from app.dependencies import get_current_user
from typing import Optional
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/audit", tags=["Audit"])


def _to_dict_list(items):
    """Helper to convert SQLAlchemy models to plain dicts for JSON serialization."""
    result = []
    for item in items:
        d = {}
        for col in item.__table__.columns:
            val = getattr(item, col.name)
            if val is not None and hasattr(val, 'isoformat'):
                val = val.isoformat()
            elif val is not None and hasattr(val, 'value'):
                val = val.value
            d[col.name] = val
        result.append(d)
    return result


async def _get_user_accessible_host_ids(user: User, db: AsyncSession) -> set[int] | None:
    """Get host IDs accessible by the user. Returns None if admin (all hosts)."""
    if user.is_admin:
        return None

    host_ids = set()

    # Hosts via direct user permissions
    perm_result = await db.execute(
        select(HostPermission.host_id).where(
            HostPermission.user_id == user.id,
            HostPermission.is_active == True,
        )
    )
    host_ids.update(r[0] for r in perm_result.all())

    # Hosts via team memberships
    team_result = await db.execute(
        select(TeamMember.team_id).where(TeamMember.user_id == user.id)
    )
    team_ids = [r[0] for r in team_result.all()]
    if team_ids:
        team_perm_result = await db.execute(
            select(HostPermission.host_id).where(
                HostPermission.team_id.in_(team_ids),
                HostPermission.is_active == True,
            )
        )
        host_ids.update(r[0] for r in team_perm_result.all())

    # Hosts via temporary permissions
    now = datetime.now(timezone.utc)
    temp_result = await db.execute(
        select(TemporaryPermission.host_id).where(
            TemporaryPermission.user_id == user.id,
            TemporaryPermission.is_revoked == False,
            TemporaryPermission.expires_at > now,
        )
    )
    host_ids.update(r[0] for r in temp_result.all())

    return host_ids


@router.get("/sessions", summary="获取会话审计列表")
async def list_audit_sessions(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    host_id: Optional[int] = None,
    status: Optional[SessionStatus] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)

    query = select(SSHSession).order_by(desc(SSHSession.started_at))
    count_query = select(func.count()).select_from(SSHSession)
    if user_id:
        query = query.where(SSHSession.user_id == user_id)
        count_query = count_query.where(SSHSession.user_id == user_id)
    if host_id:
        query = query.where(SSHSession.host_id == host_id)
        count_query = count_query.where(SSHSession.host_id == host_id)
    if status:
        query = query.where(SSHSession.status == status)
        count_query = count_query.where(SSHSession.status == status)
    if keyword:
        like_filter = (
            (SSHSession.session_id.ilike(f"%{keyword}%")) |
            (SSHSession.client_ip.ilike(f"%{keyword}%"))
        )
        query = query.where(like_filter)
        count_query = count_query.where(like_filter)
    # Non-admin: only sessions on accessible hosts
    if accessible_host_ids is not None:
        if accessible_host_ids:
            query = query.where(SSHSession.host_id.in_(accessible_host_ids))
            count_query = count_query.where(SSHSession.host_id.in_(accessible_host_ids))
        else:
            query = query.where(False)
            count_query = count_query.where(False)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": _to_dict_list(items)}


@router.get("/commands", summary="获取命令审计列表")
async def list_audit_commands(
    skip: int = 0,
    limit: int = 50,
    risk_level: Optional[RiskLevel] = None,
    session_id: Optional[int] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)

    query = select(SessionCommand).order_by(desc(SessionCommand.executed_at))
    count_query = select(func.count()).select_from(SessionCommand)
    if risk_level:
        query = query.where(SessionCommand.risk_level == risk_level)
        count_query = count_query.where(SessionCommand.risk_level == risk_level)
    if session_id:
        query = query.where(SessionCommand.session_id == session_id)
        count_query = count_query.where(SessionCommand.session_id == session_id)
    if keyword:
        query = query.where(SessionCommand.command.ilike(f"%{keyword}%"))
        count_query = count_query.where(SessionCommand.command.ilike(f"%{keyword}%"))
    # Non-admin: only commands from sessions on accessible hosts
    if accessible_host_ids is not None:
        accessible_sessions = select(SSHSession.id).where(
            SSHSession.host_id.in_(accessible_host_ids) if accessible_host_ids else False
        )
        if accessible_host_ids:
            query = query.where(SessionCommand.session_id.in_(accessible_sessions))
            count_query = count_query.where(SessionCommand.session_id.in_(accessible_sessions))
        else:
            query = query.where(False)
            count_query = count_query.where(False)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": _to_dict_list(items)}


@router.get("/login-logs", summary="获取登录日志")
async def list_login_logs(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(LoginLog).order_by(desc(LoginLog.login_at))
    count_query = select(func.count()).select_from(LoginLog)
    if user_id:
        query = query.where(LoginLog.user_id == user_id)
        count_query = count_query.where(LoginLog.user_id == user_id)
    if keyword:
        like_filter = (
            (LoginLog.username.ilike(f"%{keyword}%")) |
            (LoginLog.login_ip.ilike(f"%{keyword}%"))
        )
        query = query.where(like_filter)
        count_query = count_query.where(like_filter)
    if not current_user.is_admin:
        query = query.where(LoginLog.user_id == current_user.id)
        count_query = count_query.where(LoginLog.user_id == current_user.id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": _to_dict_list(items)}


@router.get("/risk-commands", summary="获取风险命令列表")
async def list_risk_commands(
    skip: int = 0,
    limit: int = 50,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)

    base_filter = SessionCommand.risk_level.in_([RiskLevel.warning, RiskLevel.danger])
    query = select(SessionCommand).where(base_filter).order_by(desc(SessionCommand.executed_at))
    count_query = select(func.count()).select_from(SessionCommand).where(base_filter)
    if keyword:
        query = query.where(SessionCommand.command.ilike(f"%{keyword}%"))
        count_query = count_query.where(SessionCommand.command.ilike(f"%{keyword}%"))
    # Non-admin: only risk commands from sessions on accessible hosts
    if accessible_host_ids is not None:
        if accessible_host_ids:
            accessible_sessions = select(SSHSession.id).where(
                SSHSession.host_id.in_(accessible_host_ids)
            )
            query = query.where(SessionCommand.session_id.in_(accessible_sessions))
            count_query = count_query.where(SessionCommand.session_id.in_(accessible_sessions))
        else:
            query = query.where(False)
            count_query = count_query.where(False)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": _to_dict_list(items)}


@router.get("/export/commands", summary="导出命令审计")
async def export_commands(
    format: str = "json",
    risk_level: Optional[RiskLevel] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)

    query = select(SessionCommand).order_by(desc(SessionCommand.executed_at))
    if risk_level:
        query = query.where(SessionCommand.risk_level == risk_level)
    # Non-admin: only commands from sessions on accessible hosts
    if accessible_host_ids is not None:
        if accessible_host_ids:
            accessible_sessions = select(SSHSession.id).where(
                SSHSession.host_id.in_(accessible_host_ids)
            )
            query = query.where(SessionCommand.session_id.in_(accessible_sessions))
        else:
            query = query.where(False)
    result = await db.execute(query.limit(10000))
    commands = result.scalars().all()

    if format == "json":
        import json
        data = [
            {
                "id": c.id,
                "session_id": c.session_id,
                "command": c.command,
                "risk_level": c.risk_level.value,
                "is_blocked": c.is_blocked,
                "executed_at": c.executed_at.isoformat() if c.executed_at else None,
            }
            for c in commands
        ]
        return {"format": "json", "count": len(data), "data": data}
    elif format == "csv":
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "session_id", "command", "risk_level", "is_blocked", "executed_at"])
        for c in commands:
            writer.writerow([c.id, c.session_id, c.command, c.risk_level.value, c.is_blocked, c.executed_at])
        return {"format": "csv", "count": len(commands), "data": output.getvalue()}
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use json or csv.")


# ===== SSH Login Log Analysis =====
@router.get("/ssh-login-logs", summary="获取SSH登录日志")
async def list_ssh_login_logs(
    host_id: Optional[int] = None,
    user_id: Optional[int] = None,
    risk_level: Optional[str] = None,
    is_success: Optional[bool] = None,
    keyword: Optional[str] = None,
    hours: int = 24,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    filters = [SSHLoginLog.login_at >= since]
    if host_id:
        filters.append(SSHLoginLog.host_id == host_id)
    if risk_level:
        filters.append(SSHLoginLog.risk_level == risk_level)
    if is_success is not None:
        filters.append(SSHLoginLog.is_success == is_success)
    if keyword:
        host_ids_result = await db.execute(
            select(Host.id).where(Host.name.ilike(f"%{keyword}%"))
        )
        matched_host_ids = [r[0] for r in host_ids_result.all()]
        kw_filter = (
            (SSHLoginLog.username.ilike(f"%{keyword}%")) |
            (SSHLoginLog.login_ip.ilike(f"%{keyword}%"))
        )
        if matched_host_ids:
            kw_filter = kw_filter | SSHLoginLog.host_id.in_(matched_host_ids)
        filters.append(kw_filter)
    # Non-admin: only logs from accessible hosts
    if accessible_host_ids is not None:
        if accessible_host_ids:
            filters.append(SSHLoginLog.host_id.in_(accessible_host_ids))
        else:
            filters.append(False)

    base_query = select(SSHLoginLog).where(and_(*filters))
    count_query = select(func.count()).select_from(SSHLoginLog).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = base_query.order_by(desc(SSHLoginLog.login_at))
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()

    # 批量查询主机名
    log_host_ids = {log.host_id for log in items if log.host_id}
    host_map = {}
    if log_host_ids:
        host_res = await db.execute(select(Host.id, Host.name).where(Host.id.in_(log_host_ids)))
        for hid, hname in host_res.all():
            host_map[hid] = hname

    data = []
    for log in items:
        d = {}
        for col in log.__table__.columns:
            val = getattr(log, col.name)
            if val is not None and hasattr(val, 'isoformat'):
                val = val.isoformat()
            d[col.name] = val
        d["host_name"] = host_map.get(log.host_id)
        data.append(d)
    return {"total": total, "items": data}


@router.get("/ssh-login-logs/analysis", response_model=SSHLoginAnalysisSummary, summary="SSH登录日志分析")
async def ssh_login_analysis(
    host_id: Optional[int] = None,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    filters = [SSHLoginLog.login_at >= since]
    if host_id:
        filters.append(SSHLoginLog.host_id == host_id)
    # Non-admin: only logs from accessible hosts
    if accessible_host_ids is not None:
        if accessible_host_ids:
            filters.append(SSHLoginLog.host_id.in_(accessible_host_ids))
        else:
            filters.append(False)

    # 基础统计
    total_result = await db.execute(
        select(func.count()).select_from(SSHLoginLog).where(and_(*filters))
    )
    total_logins = total_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count()).select_from(SSHLoginLog).where(and_(*filters, SSHLoginLog.is_success == False))
    )
    failed_logins = failed_result.scalar() or 0

    unique_ips_result = await db.execute(
        select(func.count(func.distinct(SSHLoginLog.login_ip))).select_from(SSHLoginLog).where(and_(*filters))
    )
    unique_ips = unique_ips_result.scalar() or 0

    unique_users_result = await db.execute(
        select(func.count(func.distinct(SSHLoginLog.username))).select_from(SSHLoginLog).where(and_(*filters))
    )
    unique_users = unique_users_result.scalar() or 0

    brute_result = await db.execute(
        select(func.count()).select_from(SSHLoginLog).where(and_(*filters, SSHLoginLog.is_brute_force == True))
    )
    brute_force_attempts = brute_result.scalar() or 0

    new_ip_result = await db.execute(
        select(func.count()).select_from(SSHLoginLog).where(and_(*filters, SSHLoginLog.is_new_ip == True))
    )
    new_ip_logins = new_ip_result.scalar() or 0

    # Top source IPs
    top_ips_result = await db.execute(
        select(SSHLoginLog.login_ip, func.count().label("cnt"))
        .where(and_(*filters))
        .group_by(SSHLoginLog.login_ip)
        .order_by(desc(func.count()))
        .limit(10)
    )
    top_source_ips = [{"ip": ip, "count": cnt} for ip, cnt in top_ips_result.all() if ip]

    # Top users
    top_users_result = await db.execute(
        select(SSHLoginLog.username, func.count().label("cnt"))
        .where(and_(*filters))
        .group_by(SSHLoginLog.username)
        .order_by(desc(func.count()))
        .limit(10)
    )
    top_users = [{"username": u, "count": cnt} for u, cnt in top_users_result.all() if u]

    # Hourly trend (PostgreSQL compatible)
    hour_expr = func.to_char(SSHLoginLog.login_at, 'YYYY-MM-DD HH24:00').label("hour")
    # Build hourly filters (same as main filters)
    hourly_filters = [SSHLoginLog.login_at >= since]
    if host_id:
        hourly_filters.append(SSHLoginLog.host_id == host_id)
    if accessible_host_ids is not None:
        if accessible_host_ids:
            hourly_filters.append(SSHLoginLog.host_id.in_(accessible_host_ids))
        else:
            hourly_filters.append(False)

    hourly_result = await db.execute(
        select(hour_expr, func.count().label("cnt"))
        .where(and_(*hourly_filters))
        .group_by(hour_expr)
        .order_by(hour_expr)
    )
    hourly_trend = [{"hour": h, "count": cnt} for h, cnt in hourly_result.all() if h]

    # Risk distribution
    risk_result = await db.execute(
        select(SSHLoginLog.risk_level, func.count().label("cnt"))
        .where(and_(*filters))
        .group_by(SSHLoginLog.risk_level)
    )
    risk_distribution = [{"level": lvl, "count": cnt} for lvl, cnt in risk_result.all()]

    return SSHLoginAnalysisSummary(
        total_logins=total_logins,
        failed_logins=failed_logins,
        unique_ips=unique_ips,
        unique_users=unique_users,
        brute_force_attempts=brute_force_attempts,
        new_ip_logins=new_ip_logins,
        top_source_ips=top_source_ips,
        top_users=top_users,
        hourly_trend=hourly_trend,
        risk_distribution=risk_distribution,
    )


@router.post("/ssh-login-logs/collect", summary="手动触发SSH登录日志采集")
async def trigger_ssh_log_collect(
    host_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    from app.core.ssh_log_collector import collect_host_ssh_logs, analyze_ssh_logs

    result = await db.execute(select(Host))
    hosts = result.scalars().all()
    total = 0
    for host in hosts:
        if host_id and host.id != host_id:
            continue
        try:
            n = await collect_host_ssh_logs(host, db)
            total += n
        except Exception as e:
            from app.core.logger import logger
            logger.error(f"Manual collect error for host {host.name}: {e}")
    if total > 0:
        await analyze_ssh_logs(db)
    return {"message": f"Collected {total} new SSH login records", "count": total}

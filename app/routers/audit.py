from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from app.database import get_db
from app.models.session import SSHSession, SessionCommand, SessionStatus, RiskLevel
from app.models.log import LoginLog, OperationLog
from app.models.user import User
from app.models.ssh_login_log import SSHLoginLog
from app.models.host import Host
from app.schemas.session import SSHSessionResponse, SessionCommandResponse
from app.schemas.ssh_login_log import SSHLoginLogResponse, SSHLoginAnalysisSummary
from app.dependencies import get_current_user
from typing import Optional
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/sessions", response_model=dict, summary="获取会话审计列表")
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
    query = select(SSHSession).order_by(desc(SSHSession.started_at))
    if user_id:
        query = query.where(SSHSession.user_id == user_id)
    if host_id:
        query = query.where(SSHSession.host_id == host_id)
    if status:
        query = query.where(SSHSession.status == status)
    if keyword:
        query = query.where(
            (SSHSession.session_id.ilike(f"%{keyword}%")) |
            (SSHSession.client_ip.ilike(f"%{keyword}%"))
        )
    if not current_user.is_admin:
        query = query.where(SSHSession.user_id == current_user.id)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.get("/commands", response_model=dict, summary="获取命令审计列表")
async def list_audit_commands(
    skip: int = 0,
    limit: int = 50,
    risk_level: Optional[RiskLevel] = None,
    session_id: Optional[int] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SessionCommand).order_by(desc(SessionCommand.executed_at))
    if risk_level:
        query = query.where(SessionCommand.risk_level == risk_level)
    if session_id:
        query = query.where(SessionCommand.session_id == session_id)
    if keyword:
        query = query.where(SessionCommand.command.ilike(f"%{keyword}%"))
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.get("/login-logs", response_model=dict, summary="获取登录日志")
async def list_login_logs(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(LoginLog).order_by(desc(LoginLog.login_at))
    if user_id:
        query = query.where(LoginLog.user_id == user_id)
    if keyword:
        query = query.where(
            (LoginLog.username.ilike(f"%{keyword}%")) |
            (LoginLog.login_ip.ilike(f"%{keyword}%"))
        )
    if not current_user.is_admin:
        query = query.where(LoginLog.user_id == current_user.id)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.get("/risk-commands", response_model=dict, summary="获取风险命令列表")
async def list_risk_commands(
    skip: int = 0,
    limit: int = 50,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SessionCommand).where(
        SessionCommand.risk_level.in_([RiskLevel.warning, RiskLevel.danger])
    ).order_by(desc(SessionCommand.executed_at))
    if keyword:
        query = query.where(SessionCommand.command.ilike(f"%{keyword}%"))
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    items = result.scalars().all()
    return {"total": total, "items": items}


@router.get("/export/commands", summary="导出命令审计")
async def export_commands(
    format: str = "json",
    risk_level: Optional[RiskLevel] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SessionCommand).order_by(desc(SessionCommand.executed_at))
    if risk_level:
        query = query.where(SessionCommand.risk_level == risk_level)
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
@router.get("/ssh-login-logs", response_model=dict, summary="获取SSH登录日志")
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
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(SSHLoginLog, Host.name.label("host_name")).join(
        Host, SSHLoginLog.host_id == Host.id, isouter=True
    ).where(SSHLoginLog.login_at >= since).order_by(desc(SSHLoginLog.login_at))

    if host_id:
        query = query.where(SSHLoginLog.host_id == host_id)
    if risk_level:
        query = query.where(SSHLoginLog.risk_level == risk_level)
    if is_success is not None:
        query = query.where(SSHLoginLog.is_success == is_success)
    if keyword:
        query = query.where(
            (SSHLoginLog.username.ilike(f"%{keyword}%")) |
            (SSHLoginLog.login_ip.ilike(f"%{keyword}%")) |
            (Host.name.ilike(f"%{keyword}%"))
        )
    if not current_user.is_admin:
        query = query.where(SSHLoginLog.username == current_user.username)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0
    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.all()

    data = []
    for log, host_name in rows:
        log.host_name = host_name
        data.append(log)
    return {"total": total, "items": data}


@router.get("/ssh-login-logs/analysis", response_model=SSHLoginAnalysisSummary, summary="SSH登录日志分析")
async def ssh_login_analysis(
    host_id: Optional[int] = None,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    base_query = select(SSHLoginLog).where(SSHLoginLog.login_at >= since)
    if host_id:
        base_query = base_query.where(SSHLoginLog.host_id == host_id)

    # 基础统计
    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total_logins = total_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count()).select_from(base_query.where(SSHLoginLog.is_success == False).subquery())
    )
    failed_logins = failed_result.scalar() or 0

    unique_ips_result = await db.execute(
        select(func.count(func.distinct(SSHLoginLog.login_ip))).select_from(base_query.subquery())
    )
    unique_ips = unique_ips_result.scalar() or 0

    unique_users_result = await db.execute(
        select(func.count(func.distinct(SSHLoginLog.username))).select_from(base_query.subquery())
    )
    unique_users = unique_users_result.scalar() or 0

    brute_result = await db.execute(
        select(func.count()).select_from(base_query.where(SSHLoginLog.is_brute_force == True).subquery())
    )
    brute_force_attempts = brute_result.scalar() or 0

    new_ip_result = await db.execute(
        select(func.count()).select_from(base_query.where(SSHLoginLog.is_new_ip == True).subquery())
    )
    new_ip_logins = new_ip_result.scalar() or 0

    # Top source IPs
    top_ips_result = await db.execute(
        select(SSHLoginLog.login_ip, func.count().label("cnt"))
        .where(SSHLoginLog.login_at >= since)
        .group_by(SSHLoginLog.login_ip)
        .order_by(desc("cnt"))
        .limit(10)
    )
    top_source_ips = [{"ip": ip, "count": cnt} for ip, cnt in top_ips_result.all() if ip]

    # Top users
    top_users_result = await db.execute(
        select(SSHLoginLog.username, func.count().label("cnt"))
        .where(SSHLoginLog.login_at >= since)
        .group_by(SSHLoginLog.username)
        .order_by(desc("cnt"))
        .limit(10)
    )
    top_users = [{"username": u, "count": cnt} for u, cnt in top_users_result.all() if u]

    # Hourly trend
    hourly_result = await db.execute(
        select(
            func.strftime("%Y-%m-%d %H:00", SSHLoginLog.login_at).label("hour"),
            func.count().label("cnt"),
        )
        .where(SSHLoginLog.login_at >= since)
        .group_by("hour")
        .order_by("hour")
    )
    hourly_trend = [{"hour": h, "count": cnt} for h, cnt in hourly_result.all() if h]

    # Risk distribution
    risk_result = await db.execute(
        select(SSHLoginLog.risk_level, func.count().label("cnt"))
        .where(SSHLoginLog.login_at >= since)
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
            logger.error(f"Manual collect error for host {host.name}: {e}")
    if total > 0:
        await analyze_ssh_logs(db)
    return {"message": f"Collected {total} new SSH login records", "count": total}


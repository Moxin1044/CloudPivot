from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.host import Host, HostStatus
from app.models.session import SSHSession, SessionCommand, SessionStatus, RiskLevel
from app.models.monitor import HostMetric, AlertRule, AlertRecord, AlertSeverity, AlertStatus
from app.models.docker import DockerHost
from app.models.user import User
from app.schemas.dashboard import (
    DashboardResponse, DashboardOverview, ResourceUsage,
    RecentAudit, RecentAlert,
)
from app.dependencies import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse, summary="获取Dashboard数据")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Overview
    total_hosts = await db.scalar(select(func.count(Host.id)))
    online_hosts = await db.scalar(
        select(func.count(Host.id)).where(Host.status == HostStatus.online)
    )
    offline_hosts = await db.scalar(
        select(func.count(Host.id)).where(Host.status == HostStatus.offline)
    )
    active_sessions = await db.scalar(
        select(func.count(SSHSession.id)).where(SSHSession.status == SessionStatus.active)
    )
    total_users = await db.scalar(select(func.count(User.id)))
    active_alerts = await db.scalar(
        select(func.count(AlertRecord.id)).where(AlertRecord.status == AlertStatus.pending)
    )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    risk_commands_today = await db.scalar(
        select(func.count(SessionCommand.id)).where(
            SessionCommand.risk_level.in_([RiskLevel.warning, RiskLevel.danger]),
            SessionCommand.executed_at >= today_start,
        )
    )

    # Docker stats
    total_containers = 0
    running_containers = 0
    try:
        from app.core.docker_client import docker_client
        containers = await docker_client.list_containers(all=True)
        total_containers = len(containers)
        running_containers = sum(1 for c in containers if c.get("State") == "running")
    except Exception:
        pass

    overview = DashboardOverview(
        total_hosts=total_hosts or 0,
        online_hosts=online_hosts or 0,
        offline_hosts=offline_hosts or 0,
        active_sessions=active_sessions or 0,
        total_containers=total_containers,
        running_containers=running_containers,
        total_users=total_users or 0,
        active_alerts=active_alerts or 0,
        risk_commands_today=risk_commands_today or 0,
    )

    # Resource usage - top 10 hosts by latest metrics
    resource_usage = []
    metric_result = await db.execute(
        select(HostMetric, Host)
        .join(Host, HostMetric.host_id == Host.id)
        .order_by(desc(HostMetric.collected_at))
        .limit(10)
    )
    seen_hosts = set()
    for metric, host in metric_result.all():
        if host.id not in seen_hosts:
            seen_hosts.add(host.id)
            resource_usage.append(ResourceUsage(
                host_id=host.id,
                host_name=host.name,
                cpu_percent=metric.cpu_percent,
                memory_percent=metric.memory_percent,
                disk_percent=metric.disk_percent,
            ))

    # Recent audits
    recent_audits = []
    audit_result = await db.execute(
        select(SessionCommand, SSHSession, User, Host)
        .join(SSHSession, SessionCommand.session_id == SSHSession.id)
        .join(User, SSHSession.user_id == User.id)
        .join(Host, SSHSession.host_id == Host.id)
        .order_by(desc(SessionCommand.executed_at))
        .limit(10)
    )
    for cmd, session, user, host in audit_result.all():
        recent_audits.append(RecentAudit(
            session_id=session.session_id,
            username=user.username,
            host_name=host.name,
            command=cmd.command,
            risk_level=cmd.risk_level.value,
            executed_at=cmd.executed_at,
        ))

    # Recent alerts
    recent_alerts = []
    alert_result = await db.execute(
        select(AlertRecord).order_by(desc(AlertRecord.created_at)).limit(10)
    )
    for alert in alert_result.scalars().all():
        recent_alerts.append(RecentAlert(
            id=alert.id,
            title=alert.title,
            severity=alert.severity.value,
            created_at=alert.created_at,
        ))

    return DashboardResponse(
        overview=overview,
        resource_usage=resource_usage,
        recent_audits=recent_audits,
        recent_alerts=recent_alerts,
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.database import get_db
from app.models.host import Host, HostStatus
from app.models.session import SSHSession, SessionCommand, SessionStatus, RiskLevel
from app.models.monitor import HostMetric, AlertRule, AlertRecord, AlertSeverity, AlertStatus
from app.models.permission import HostPermission, TemporaryPermission
from app.models.team import TeamMember
from app.models.user import User
from app.schemas.dashboard import (
    DashboardResponse, DashboardOverview, ResourceUsage,
    RecentAudit, RecentAlert,
)
from app.dependencies import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def _get_user_accessible_host_ids(user: User, db: AsyncSession) -> set[int] | None:
    """Get host IDs accessible by the user. Returns None if admin (all hosts)."""
    if user.is_admin:
        return None  # None means all hosts

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


@router.get("", response_model=DashboardResponse, summary="获取Dashboard数据")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accessible_host_ids = await _get_user_accessible_host_ids(current_user, db)
    is_admin = current_user.is_admin

    # Build host filter for non-admin users
    host_filter = True
    if accessible_host_ids is not None:
        if not accessible_host_ids:
            host_filter = False  # No accessible hosts
        else:
            host_filter = Host.id.in_(accessible_host_ids)

    # Overview - hosts
    total_hosts = await db.scalar(
        select(func.count(Host.id)).where(host_filter) if not is_admin
        else select(func.count(Host.id))
    )
    online_hosts = await db.scalar(
        select(func.count(Host.id)).where(
            and_(Host.status == HostStatus.online, host_filter if not is_admin else True)
        ) if not is_admin
        else select(func.count(Host.id)).where(Host.status == HostStatus.online)
    )
    offline_hosts = await db.scalar(
        select(func.count(Host.id)).where(
            and_(Host.status == HostStatus.offline, host_filter if not is_admin else True)
        ) if not is_admin
        else select(func.count(Host.id)).where(Host.status == HostStatus.offline)
    )

    # Sessions - for non-admin, only count sessions on accessible hosts
    if is_admin:
        active_sessions = await db.scalar(
            select(func.count(SSHSession.id)).where(SSHSession.status == SessionStatus.active)
        )
    else:
        if accessible_host_ids:
            active_sessions = await db.scalar(
                select(func.count(SSHSession.id)).where(
                    and_(
                        SSHSession.status == SessionStatus.active,
                        SSHSession.host_id.in_(accessible_host_ids),
                    )
                )
            )
        else:
            active_sessions = 0

    # Users count - only for admin
    total_users = await db.scalar(select(func.count(User.id))) if is_admin else 0

    # Active alerts - for non-admin, only from accessible hosts
    if is_admin:
        active_alerts = await db.scalar(
            select(func.count(AlertRecord.id)).where(AlertRecord.status == AlertStatus.pending)
        )
    else:
        if accessible_host_ids:
            active_alerts = await db.scalar(
                select(func.count(AlertRecord.id)).where(
                    and_(
                        AlertRecord.status == AlertStatus.pending,
                        AlertRecord.host_id.in_(accessible_host_ids),
                    )
                )
            )
        else:
            active_alerts = 0

    # Risk commands today - for non-admin, only from sessions on accessible hosts
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if is_admin:
        risk_commands_today = await db.scalar(
            select(func.count(SessionCommand.id)).where(
                SessionCommand.risk_level.in_([RiskLevel.warning, RiskLevel.danger]),
                SessionCommand.executed_at >= today_start,
            )
        )
    else:
        if accessible_host_ids:
            risk_sessions = select(SSHSession.id).where(
                SSHSession.host_id.in_(accessible_host_ids)
            )
            risk_commands_today = await db.scalar(
                select(func.count(SessionCommand.id)).where(
                    and_(
                        SessionCommand.risk_level.in_([RiskLevel.warning, RiskLevel.danger]),
                        SessionCommand.executed_at >= today_start,
                        SessionCommand.session_id.in_(risk_sessions),
                    )
                )
            )
        else:
            risk_commands_today = 0

    overview = DashboardOverview(
        total_hosts=total_hosts or 0,
        online_hosts=online_hosts or 0,
        offline_hosts=offline_hosts or 0,
        active_sessions=active_sessions or 0,
        total_users=total_users or 0,
        active_alerts=active_alerts or 0,
        risk_commands_today=risk_commands_today or 0,
    )

    # Resource usage - only from accessible hosts
    resource_usage = []
    metric_query = (
        select(HostMetric, Host)
        .join(Host, HostMetric.host_id == Host.id)
        .order_by(desc(HostMetric.collected_at))
    )
    if not is_admin and accessible_host_ids:
        metric_query = metric_query.where(Host.id.in_(accessible_host_ids))
    elif not is_admin:
        metric_query = metric_query.where(False)

    metric_result = await db.execute(metric_query.limit(50))
    seen_hosts = set()
    for metric, host in metric_result.all():
        if host.id not in seen_hosts:
            seen_hosts.add(host.id)
            if len(resource_usage) >= 10:
                break
            resource_usage.append(ResourceUsage(
                host_id=host.id,
                host_name=host.name,
                cpu_percent=metric.cpu_percent,
                memory_percent=metric.memory_percent,
                disk_percent=metric.disk_percent,
            ))

    # Recent audits - only from sessions on accessible hosts
    recent_audits = []
    audit_query = (
        select(SessionCommand, SSHSession, User, Host)
        .join(SSHSession, SessionCommand.session_id == SSHSession.id)
        .join(User, SSHSession.user_id == User.id)
        .join(Host, SSHSession.host_id == Host.id)
        .order_by(desc(SessionCommand.executed_at))
    )
    if not is_admin and accessible_host_ids:
        audit_query = audit_query.where(SSHSession.host_id.in_(accessible_host_ids))
    elif not is_admin:
        audit_query = audit_query.where(False)

    audit_result = await db.execute(audit_query.limit(10))
    for cmd, session, user, host in audit_result.all():
        recent_audits.append(RecentAudit(
            session_id=session.session_id,
            username=user.username,
            host_name=host.name,
            command=cmd.command,
            risk_level=cmd.risk_level.value,
            executed_at=cmd.executed_at,
        ))

    # Recent alerts - only from accessible hosts
    recent_alerts = []
    alert_query = select(AlertRecord).order_by(desc(AlertRecord.created_at))
    if not is_admin and accessible_host_ids:
        alert_query = alert_query.where(AlertRecord.host_id.in_(accessible_host_ids))
    elif not is_admin:
        alert_query = alert_query.where(False)

    alert_result = await db.execute(alert_query.limit(10))
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

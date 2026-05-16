from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from app.database import get_db
from app.models.monitor import HostMetric, AlertRule, AlertRecord, AlertSeverity, AlertStatus
from app.models.host import Host
from app.models.user import User
from app.schemas.monitor import (
    HostMetricResponse, AlertRuleCreate, AlertRuleResponse, AlertRecordResponse,
)
from app.dependencies import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/monitor", tags=["Monitoring"])


# ===== Host Metrics =====
@router.get("/metrics/{host_id}", response_model=list[HostMetricResponse], summary="获取主机监控指标")
async def get_host_metrics(
    host_id: int,
    hours: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(HostMetric)
        .where(HostMetric.host_id == host_id, HostMetric.collected_at >= since)
        .order_by(HostMetric.collected_at)
    )
    return result.scalars().all()


@router.get("/metrics/{host_id}/latest", response_model=Optional[HostMetricResponse], summary="获取主机最新指标")
async def get_latest_metric(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HostMetric)
        .where(HostMetric.host_id == host_id)
        .order_by(desc(HostMetric.collected_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


# ===== Alert Rules =====
@router.get("/alert-rules", response_model=list[AlertRuleResponse], summary="获取告警规则列表")
async def list_alert_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRule))
    return result.scalars().all()


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED, summary="创建告警规则")
async def create_alert_rule(
    data: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse, summary="更新告警规则")
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/alert-rules/{rule_id}", summary="删除告警规则")
async def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    await db.delete(rule)
    return {"message": "Alert rule deleted"}


# ===== Alert Records =====
@router.get("/alerts", response_model=list[AlertRecordResponse], summary="获取告警记录")
async def list_alerts(
    severity: Optional[AlertSeverity] = None,
    status: Optional[AlertStatus] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AlertRecord).order_by(desc(AlertRecord.created_at))
    if severity:
        query = query.where(AlertRecord.severity == severity)
    if status:
        query = query.where(AlertRecord.status == status)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/alerts/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRecord).where(AlertRecord.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.acknowledged
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Alert acknowledged"}


@router.post("/alerts/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRecord).where(AlertRecord.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.resolved
    alert.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Alert resolved"}


# ===== Agent Data Ingestion =====
@router.post("/agent/report", summary="Agent上报监控数据")
async def agent_report(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Endpoint for cloudpivot-agent to push metrics."""
    host_id = data.get("host_id")
    if not host_id:
        raise HTTPException(status_code=400, detail="host_id required")

    metric = HostMetric(
        host_id=host_id,
        cpu_percent=data.get("cpu_percent"),
        memory_percent=data.get("memory_percent"),
        memory_used_gb=data.get("memory_used_gb"),
        memory_total_gb=data.get("memory_total_gb"),
        disk_percent=data.get("disk_percent"),
        disk_used_gb=data.get("disk_used_gb"),
        disk_total_gb=data.get("disk_total_gb"),
        network_in_mbps=data.get("network_in_mbps"),
        network_out_mbps=data.get("network_out_mbps"),
        load_1min=data.get("load_1min"),
        load_5min=data.get("load_5min"),
        load_15min=data.get("load_15min"),
        extra_data=data.get("extra_data"),
    )
    db.add(metric)

    # Update host status
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if host:
        host.status = "online"

    await db.flush()

    # Check alert rules
    await _check_alert_rules(host_id, data, db)

    return {"status": "ok"}


async def _check_alert_rules(host_id: int, metrics: dict, db: AsyncSession):
    """Check if any alert rules are triggered by the new metrics."""
    result = await db.execute(
        select(AlertRule).where(AlertRule.is_enabled == True)
    )
    rules = result.scalars().all()

    for rule in rules:
        if rule.host_id and rule.host_id != host_id:
            continue

        metric_value = metrics.get(rule.metric_type)
        if metric_value is None:
            continue

        triggered = False
        if rule.condition == "gt" and metric_value > rule.threshold:
            triggered = True
        elif rule.condition == "lt" and metric_value < rule.threshold:
            triggered = True
        elif rule.condition == "gte" and metric_value >= rule.threshold:
            triggered = True
        elif rule.condition == "lte" and metric_value <= rule.threshold:
            triggered = True
        elif rule.condition == "eq" and metric_value == rule.threshold:
            triggered = True

        if triggered:
            alert = AlertRecord(
                rule_id=rule.id,
                host_id=host_id,
                severity=rule.severity,
                title=f"{rule.name} - {rule.metric_type} {rule.condition} {rule.threshold}",
                message=f"Current value: {metric_value}",
                notified_channels=rule.notify_channels,
            )
            db.add(alert)
            await db.flush()

            # Send notifications to all admin users and team members
            await _send_alert_notifications(alert, rule, db)


async def _send_alert_notifications(alert: AlertRecord, rule: AlertRule, db: AsyncSession):
    """Send alert notifications using each user's personal notification settings."""
    import asyncio
    from app.models.user import User, UserRole
    from app.core.logger import logger

    # Collect all users who should be notified: admins + team members
    notify_users = []

    # All admins
    admin_result = await db.execute(
        select(User).where(User.role == UserRole.admin, User.status == "active")
    )
    notify_users.extend(admin_result.scalars().all())

    # Team members (if rule is scoped to a team)
    if rule.team_id:
        from app.models.team import TeamMember
        member_result = await db.execute(
            select(User)
            .join(TeamMember, TeamMember.user_id == User.id)
            .where(TeamMember.team_id == rule.team_id, User.status == "active")
        )
        for u in member_result.scalars().all():
            if u not in notify_users:
                notify_users.append(u)

    # Send to each user via their personal channels
    for user in notify_users:
        channels = (user.notify_channels or "").split(",") if user.notify_channels else []
        if not channels:
            continue

        title = f"[CloudPivot Alert] {alert.title}"
        message = f"Severity: {alert.severity.value}\nHost: {alert.host_id}\n{alert.message or ''}"

        for channel in channels:
            channel = channel.strip()
            try:
                if channel == "email" and user.notification_email:
                    from app.services.notification import notification_service
                    asyncio.create_task(
                        notification_service.send_email(user.notification_email, title, message)
                    )
                elif channel == "feishu" and user.feishu_webhook:
                    from app.services.notification import notification_service
                    asyncio.create_task(
                        notification_service.send_feishu(user.feishu_webhook, title, message)
                    )
                elif channel == "dingtalk" and user.dingtalk_webhook:
                    from app.services.notification import notification_service
                    asyncio.create_task(
                        notification_service.send_dingtalk(user.dingtalk_webhook, title, message)
                    )
                elif channel == "webhook" and rule.webhook_url:
                    from app.services.notification import notification_service
                    asyncio.create_task(
                        notification_service.send_webhook(rule.webhook_url, {
                            "alert_id": alert.id,
                            "title": alert.title,
                            "severity": alert.severity.value,
                            "message": alert.message,
                        })
                    )
            except Exception as e:
                logger.error(f"Failed to send {channel} notification to user {user.id}: {e}")

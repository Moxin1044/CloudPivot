from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.session import SSHSession, SessionCommand, SessionStatus, RiskLevel
from app.models.log import LoginLog, OperationLog
from app.models.user import User
from app.schemas.session import SSHSessionResponse, SessionCommandResponse
from app.dependencies import get_current_user
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/sessions", response_model=list[SSHSessionResponse], summary="获取会话审计列表")
async def list_audit_sessions(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[int] = None,
    host_id: Optional[int] = None,
    status: Optional[SessionStatus] = None,
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
    if not current_user.is_admin:
        query = query.where(SSHSession.user_id == current_user.id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/commands", response_model=list[SessionCommandResponse], summary="获取命令审计列表")
async def list_audit_commands(
    skip: int = 0,
    limit: int = 50,
    risk_level: Optional[RiskLevel] = None,
    session_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SessionCommand).order_by(desc(SessionCommand.executed_at))
    if risk_level:
        query = query.where(SessionCommand.risk_level == risk_level)
    if session_id:
        query = query.where(SessionCommand.session_id == session_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/login-logs", summary="获取登录日志")
async def list_login_logs(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(LoginLog).order_by(desc(LoginLog.login_at))
    if user_id:
        query = query.where(LoginLog.user_id == user_id)
    if not current_user.is_admin:
        query = query.where(LoginLog.user_id == current_user.id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/risk-commands", response_model=list[SessionCommandResponse], summary="获取风险命令列表")
async def list_risk_commands(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SessionCommand)
        .where(SessionCommand.risk_level.in_([RiskLevel.warning, RiskLevel.danger]))
        .order_by(desc(SessionCommand.executed_at))
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


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

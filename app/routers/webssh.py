from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import asyncssh
import json
import uuid
import time
from datetime import datetime, timezone
from app.database import get_db
from app.models.host import Host
from app.models.session import SSHSession, SessionCommand, SessionRecording, SessionStatus, RiskLevel
from app.models.permission import HostPermission, PermissionLevel, TemporaryPermission
from app.models.user import User
from app.dependencies import get_current_user
from app.core.websocket import ws_manager, WebSSHSession
from app.core.security import decode_token
from app.config import settings
from app.core.logger import logger

router = APIRouter(tags=["WebSSH"])

# Risk command patterns
RISK_PATTERNS = {
    RiskLevel.danger: [
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:",
        "shutdown", "poweroff", "reboot", "init 0", "init 6",
        "> /dev/sda", "chmod -R 777 /",
    ],
    RiskLevel.warning: [
        "rm -rf", "rm -r", "chmod 777", "chown -R",
        "kill -9", "pkill", "killall",
        "iptables -F", "ufw disable",
        "userdel", "usermod -L", "passwd -l",
        "service stop", "systemctl stop", "systemctl disable",
    ],
}

UPLOAD_COMMANDS = ["scp", "rsync", "rz", "sz", "sftp"]


def check_command_risk(command: str) -> RiskLevel:
    cmd = command.strip().lower()
    for pattern in RISK_PATTERNS.get(RiskLevel.danger, []):
        if pattern.lower() in cmd:
            return RiskLevel.danger
    for pattern in RISK_PATTERNS.get(RiskLevel.warning, []):
        if pattern.lower() in cmd:
            return RiskLevel.warning
    return RiskLevel.safe


def check_permission_level(host_permission, command: str) -> tuple[bool, RiskLevel]:
    """Check if the command is allowed based on permission level."""
    risk = check_command_risk(command)

    if risk == RiskLevel.danger:
        return False, risk

    if host_permission.permission_level == PermissionLevel.readonly:
        # readonly: only allow viewing commands
        safe_prefixes = ("cat ", "less ", "more ", "head ", "tail ", "ls", "pwd",
                         "whoami", "id", "uname", "df", "free", "top", "ps",
                         "netstat", "ss ", "ip ", "ifconfig", "echo", "which", "type ")
        if not any(command.strip().lower().startswith(p) for p in safe_prefixes):
            return False, RiskLevel.warning

    if not host_permission.can_execute and risk != RiskLevel.safe:
        return False, risk

    if not host_permission.can_upload:
        for upload_cmd in UPLOAD_COMMANDS:
            if upload_cmd in command.lower():
                return False, RiskLevel.warning

    return True, risk


@router.websocket("/ws/ssh/{host_id}")
async def websocket_ssh(
    websocket: WebSocket,
    host_id: int,
    token: str = Query(...),
    db_session=None,
):
    # Authenticate via token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id = int(payload.get("sub"))
    await websocket.accept(subprotocol="binary")

    # Get DB session
    from app.database import async_session
    async with async_session() as db:
        # Get user
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            await websocket.close(code=4003, reason="User not found or inactive")
            return

        # Get host
        host_result = await db.execute(select(Host).where(Host.id == host_id))
        host = host_result.scalar_one_or_none()
        if not host:
            await websocket.close(code=4004, reason="Host not found")
            return

        # Check session limit
        if ws_manager.get_user_session_count(user_id) >= settings.WEBSSH_SSH_TIMEOUT:
            await websocket.close(code=4005, reason="Max sessions reached")
            return

        # Connect to SSH
        try:
            connect_kwargs = {
                "host": host.ip_address,
                "port": host.port,
                "username": host.username,
                "known_hosts": None,
                "connect_timeout": settings.WEBSSH_SSH_TIMEOUT,
            }
            if host.auth_type.value == "key" and host.private_key_encrypted:
                pk = host.private_key_encrypted
                if "-----BEGIN" in pk:
                    connect_kwargs["client_keys"] = [asyncssh.import_private_key(pk)]
                else:
                    connect_kwargs["client_keys"] = [pk]
            elif host.password_encrypted:
                connect_kwargs["password"] = host.password_encrypted

            ssh_conn = await asyncssh.connect(**connect_kwargs)
        except Exception as e:
            await websocket.send_json({"type": "error", "message": f"SSH connection failed: {e}"})
            await websocket.close(code=4006, reason="SSH connection failed")
            return

        # Create session record
        session_id = str(uuid.uuid4())
        ssh_session = SSHSession(
            session_id=session_id,
            user_id=user.id,
            host_id=host.id,
            client_ip=websocket.client.host if websocket.client else None,
            status=SessionStatus.active,
        )
        db.add(ssh_session)
        await db.flush()

        # Setup WebSSH session
        webssh_session = WebSSHSession(
            session_id=session_id,
            user_id=user.id,
            host_id=host.id,
            websocket=websocket,
        )
        ws_manager.add_session(webssh_session)

        # Start shell
        term_type = "xterm-256color"
        term_size = (80, 24)
        try:
            async with ssh_conn.create_process(
                term_type=term_type,
                term_size=term_size,
            ) as process:
                webssh_session.ssh_writer = process.stdin
                webssh_session.ssh_reader = process.stdout

                # Send connected message
                await websocket.send_json({
                    "type": "connected",
                    "session_id": session_id,
                    "host": host.ip_address,
                    "username": host.username,
                })

                # Read from SSH and forward to WebSocket
                async def read_ssh():
                    try:
                        while True:
                            data = await process.stdout.read(4096)
                            if not data:
                                break
                            if isinstance(data, str):
                                await websocket.send_text(data)
                            else:
                                await websocket.send_bytes(data)
                    except Exception:
                        pass

                # Read from WebSocket and forward to SSH
                async def read_ws():
                    try:
                        while True:
                            data = await websocket.receive_text()
                            try:
                                msg = json.loads(data)
                                msg_type = msg.get("type", "input")

                                if msg_type == "input":
                                    command = msg.get("data", "")
                                    # Check permission and risk
                                    perm_result = await db.execute(
                                        select(HostPermission).where(
                                            HostPermission.host_id == host_id,
                                            HostPermission.is_active == True,
                                        ).limit(1)
                                    )
                                    perm = perm_result.scalar_one_or_none()

                                    if perm:
                                        allowed, risk = check_permission_level(perm, command)
                                        if not allowed:
                                            await websocket.send_json({
                                                "type": "blocked",
                                                "command": command,
                                                "risk": risk.value,
                                                "message": f"Command blocked (risk: {risk.value})",
                                            })
                                            # Log blocked command
                                            cmd_log = SessionCommand(
                                                session_id=ssh_session.id,
                                                command=command,
                                                risk_level=risk,
                                                is_blocked=True,
                                            )
                                            db.add(cmd_log)
                                            await db.commit()
                                            continue

                                    # Log command
                                    risk = check_command_risk(command)
                                    cmd_log = SessionCommand(
                                        session_id=ssh_session.id,
                                        command=command,
                                        risk_level=risk,
                                        is_blocked=False,
                                    )
                                    db.add(cmd_log)
                                    await db.commit()

                                    # Send to SSH
                                    process.stdin.write(command)
                                    await process.stdin.drain()

                                elif msg_type == "resize":
                                    cols = msg.get("cols", 80)
                                    rows = msg.get("rows", 24)
                                    process.resize(cols, rows)

                                elif msg_type == "ping":
                                    await websocket.send_json({"type": "pong"})

                            except json.JSONDecodeError:
                                process.stdin.write(data)
                                await process.stdin.drain()
                    except WebSocketDisconnect:
                        pass
                    except Exception:
                        pass

                # Run both tasks
                read_task = asyncio.create_task(read_ssh())
                write_task = asyncio.create_task(read_ws())

                try:
                    done, pending = await asyncio.wait(
                        [read_task, write_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                finally:
                    # Update session
                    ssh_session.status = SessionStatus.closed
                    ssh_session.ended_at = datetime.now(timezone.utc)
                    if ssh_session.started_at:
                        duration = (ssh_session.ended_at - ssh_session.started_at).total_seconds()
                        ssh_session.duration_seconds = int(duration)
                    await db.flush()
                    await db.commit()

        except Exception as e:
            logger.error(f"WebSSH error: {e}")
        finally:
            ws_manager.remove_session(session_id)
            try:
                ssh_conn.close()
                await ssh_conn.wait_closed()
            except Exception:
                pass
            try:
                await websocket.close()
            except Exception:
                pass


@router.get("/sessions", summary="获取会话列表")
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(SSHSession).order_by(SSHSession.started_at.desc())
    if not current_user.is_admin:
        query = query.where(SSHSession.user_id == current_user.id)
    result = await db.execute(query.offset(skip).limit(limit))
    sessions = result.scalars().all()
    return sessions


@router.get("/sessions/{session_id}/commands", summary="获取会话命令记录")
async def get_session_commands(
    session_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SessionCommand)
        .where(SessionCommand.session_id == session_id)
        .order_by(SessionCommand.executed_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/recording", summary="获取会话录屏记录")
async def get_session_recording(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SessionRecording).where(SessionRecording.session_id == session_id)
    )
    recording = result.scalar_one_or_none()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording


@router.get("/active-sessions", summary="获取活跃会话")
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SSHSession).where(SSHSession.status == SessionStatus.active)
    )
    return result.scalars().all()

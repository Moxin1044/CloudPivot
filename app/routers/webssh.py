from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import asyncssh
import json
import uuid
import time
from datetime import datetime, timezone
from app.database import get_db, async_session
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
):
    # Authenticate via token
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id = int(payload.get("sub"))
    await websocket.accept()

    # Initial setup with DB
    host = None
    ssh_conn = None
    ssh_session = None
    session_id = str(uuid.uuid4())

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
        if ws_manager.get_user_session_count(user_id) >= settings.WEBSSH_MAX_SESSIONS_PER_USER:
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
            await websocket.send_json({"_sys": True, "type": "error", "message": f"SSH connection failed: {e}"})
            await websocket.close(code=4006, reason="SSH connection failed")
            return

        # Create session record — MUST commit so foreign keys work later
        ssh_session = SSHSession(
            session_id=session_id,
            user_id=user.id,
            host_id=host.id,
            client_ip=websocket.client.host if websocket.client else None,
            status=SessionStatus.active,
        )
        db.add(ssh_session)
        await db.commit()

        # Setup WebSSH session
        webssh_session = WebSSHSession(
            session_id=session_id,
            user_id=user.id,
            host_id=host.id,
            websocket=websocket,
        )
        ws_manager.add_session(webssh_session)

    # Start shell
    process = None
    try:
        process = await ssh_conn.create_process(
            term_type="xterm",
            term_size=(24, 80),
        )
        webssh_session.ssh_writer = process.stdin
        webssh_session.ssh_reader = process.stdout

        # Send connected message
        await websocket.send_json({
            "_sys": True,
            "type": "connected",
            "session_id": session_id,
            "host": host.ip_address,
            "username": host.username,
        })

        # Use two concurrent tasks: one reading SSH output, one reading WebSocket input
        cmd_buffer = ""

        async def read_ssh():
            """Read from SSH and forward to WebSocket."""
            try:
                while True:
                    data = await process.stdout.read(4096)
                    if not data:
                        return "ssh_closed"
                    if isinstance(data, str):
                        await websocket.send_text(data)
                    else:
                        await websocket.send_bytes(data)
            except Exception as e:
                logger.error(f"read_ssh error: {e}")
                return "ssh_error"

        async def read_ws():
            """Read from WebSocket and forward to SSH."""
            nonlocal cmd_buffer
            while True:
                # Receive message
                try:
                    raw = await websocket.receive_text()
                except WebSocketDisconnect:
                    return "ws_closed"
                except Exception as e:
                    logger.error(f"read_ws receive error: {e}")
                    return "ws_error"

                # Parse JSON
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    # Non-JSON: forward raw
                    try:
                        process.stdin.write(raw)
                        await process.stdin.drain()
                    except Exception as e:
                        logger.error(f"stdin write error: {e}")
                        return "ssh_error"
                    continue

                msg_type = msg.get("type", "input")

                if msg_type == "input":
                    char = msg.get("data", "")
                    if not char:
                        continue

                    if char == "\r" or char == "\n":
                        command = cmd_buffer.strip()
                        cmd_buffer = ""
                        if command:
                            # Check permissions and log command
                            try:
                                async with async_session() as perm_db:
                                    perm_result = await perm_db.execute(
                                        select(HostPermission).where(
                                            HostPermission.host_id == host_id,
                                            HostPermission.is_active == True,
                                        ).limit(1)
                                    )
                                    perm = perm_result.scalar_one_or_none()

                                    blocked = False
                                    risk = RiskLevel.safe
                                    if perm:
                                        allowed, risk = check_permission_level(perm, command)
                                        if not allowed:
                                            blocked = True
                                            process.stdin.write("\x03")
                                            await process.stdin.drain()
                                            await websocket.send_json({
                                                "_sys": True,
                                                "type": "blocked",
                                                "command": command,
                                                "risk": risk.value,
                                                "message": f"Command blocked (risk: {risk.value})",
                                            })
                                            perm_db.add(SessionCommand(
                                                session_id=ssh_session.id,
                                                command=command,
                                                risk_level=risk,
                                                is_blocked=True,
                                            ))
                                            await perm_db.commit()

                                    if not blocked:
                                        risk = check_command_risk(command)
                                        perm_db.add(SessionCommand(
                                            session_id=ssh_session.id,
                                            command=command,
                                            risk_level=risk,
                                            is_blocked=False,
                                        ))
                                        await perm_db.commit()
                                        process.stdin.write(char)
                                        await process.stdin.drain()
                            except Exception as e:
                                logger.error(f"Permission check error: {e}")
                                # On DB error, still forward the character to avoid disconnect
                                process.stdin.write(char)
                                await process.stdin.drain()
                        else:
                            # Empty command, just forward the enter key
                            process.stdin.write(char)
                            await process.stdin.drain()
                    elif char == "\x7f" or char == "\b":
                        if cmd_buffer:
                            cmd_buffer = cmd_buffer[:-1]
                        process.stdin.write("\x7f")
                        await process.stdin.drain()
                    elif char == "\x03":
                        cmd_buffer = ""
                        process.stdin.write("\x03")
                        await process.stdin.drain()
                    else:
                        cmd_buffer += char
                        try:
                            process.stdin.write(char)
                            await process.stdin.drain()
                        except Exception as e:
                            logger.error(f"stdin write error: {e}")
                            return "ssh_error"

                elif msg_type == "resize":
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    process.resize(cols, rows)

                elif msg_type == "ping":
                    await websocket.send_json({"_sys": True, "type": "pong"})

        # Run both tasks concurrently — when either finishes (error/close), the other is cancelled
        ssh_task = asyncio.create_task(read_ssh())
        ws_task = asyncio.create_task(read_ws())

        done, pending = await asyncio.wait(
            [ssh_task, ws_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    except Exception as e:
        logger.error(f"WebSSH error: {e}", exc_info=True)
    finally:
        # Update session using a fresh DB session
        try:
            async with async_session() as close_db:
                close_db.add(ssh_session)
                ssh_session.status = SessionStatus.closed
                ssh_session.ended_at = datetime.now(timezone.utc)
                if ssh_session.started_at:
                    duration = (ssh_session.ended_at - ssh_session.started_at).total_seconds()
                    ssh_session.duration_seconds = int(duration)
                await close_db.commit()
        except Exception:
            pass

        ws_manager.remove_session(session_id)
        try:
            if process and not process.stdin.is_closing():
                process.stdin.close()
                await process.stdin.drain()
        except Exception:
            pass
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

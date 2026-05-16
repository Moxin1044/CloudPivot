from __future__ import annotations

import asyncio
import asyncssh
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field
from app.config import settings
from app.core.logger import logger


@dataclass
class SSHConnection:
    host_id: str
    conn: asyncssh.SSHClientConnection
    created_at: float
    last_used: float


class SSHConnectionPool:
    """Manage reusable SSH connections with pooling."""

    def __init__(self, max_idle: int = 300, max_connections: int = 100):
        self._pool: Dict[str, SSHConnection] = {}
        self._lock = asyncio.Lock()
        self._max_idle = max_idle
        self._max_connections = max_connections

    async def get_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        timeout: int = None,
    ) -> asyncssh.SSHClientConnection:
        key = f"{username}@{host}:{port}"
        async with self._lock:
            if key in self._pool:
                conn_info = self._pool[key]
                if not conn_info.conn.is_closed():
                    import time
                    conn_info.last_used = time.time()
                    return conn_info.conn
                del self._pool[key]

        client_keys = None
        if private_key:
            if "-----BEGIN" in private_key:
                client_keys = [asyncssh.import_private_key(private_key)]
            else:
                client_keys = [private_key]
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None,
            "client_keys": client_keys,
            "password": password if not private_key else None,
        }
        if timeout is not None:
            connect_kwargs["connect_timeout"] = timeout
        else:
            connect_kwargs["connect_timeout"] = settings.WEBSSH_SSH_TIMEOUT

        conn = await asyncssh.connect(**connect_kwargs)

        import time
        async with self._lock:
            self._pool[key] = SSHConnection(
                host_id=key,
                conn=conn,
                created_at=time.time(),
                last_used=time.time(),
            )
        return conn

    async def release_connection(self, host: str, port: int, username: str):
        key = f"{username}@{host}:{port}"
        async with self._lock:
            if key in self._pool:
                conn_info = self._pool.pop(key)
                conn_info.conn.close()
                await conn_info.conn.wait_closed()

    async def cleanup_idle(self):
        import time
        now = time.time()
        async with self._lock:
            expired = [
                k for k, v in self._pool.items()
                if now - v.last_used > self._max_idle or v.conn.is_closed()
            ]
            for k in expired:
                conn_info = self._pool.pop(k)
                try:
                    conn_info.conn.close()
                except Exception:
                    pass

    async def close_all(self):
        async with self._lock:
            for conn_info in self._pool.values():
                try:
                    conn_info.conn.close()
                except Exception:
                    pass
            self._pool.clear()


ssh_pool = SSHConnectionPool()


async def test_ssh_connectivity(
    host: str,
    port: int,
    username: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    timeout: int = 10,
) -> Tuple[bool, str]:
    """Test SSH connectivity to a host. Returns (success, message)."""
    try:
        connect_kwargs = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None,
            "connect_timeout": timeout,
        }
        if private_key:
            if "-----BEGIN" in private_key:
                connect_kwargs["client_keys"] = [asyncssh.import_private_key(private_key)]
            else:
                connect_kwargs["client_keys"] = [private_key]
        elif password:
            connect_kwargs["password"] = password

        async with asyncssh.connect(**connect_kwargs) as conn:
            result = await conn.run("echo ok", check=True)
            if result.stdout.strip() == "ok":
                return True, "Connection successful"
            return False, "Unexpected response"
    except asyncssh.DisconnectError as e:
        return False, f"Disconnected: {e.reason}"
    except asyncssh.ConnectionLost:
        return False, "Connection lost"
    except asyncssh.PermissionDenied:
        return False, "Authentication failed"
    except asyncio.TimeoutError:
        return False, "Connection timeout"
    except OSError as e:
        return False, f"OS Error: {e}"
    except Exception as e:
        return False, f"Error: {type(e).__name__}: {e}"

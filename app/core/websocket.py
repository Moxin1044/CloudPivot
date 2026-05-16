from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, Set, Optional
from dataclasses import dataclass, field
from fastapi import WebSocket
from app.core.logger import logger


@dataclass
class WebSSHSession:
    session_id: str
    user_id: int
    host_id: int
    websocket: WebSocket
    ssh_writer: Optional[object] = None
    ssh_reader: Optional[object] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_alive: bool = True


class ConnectionManager:
    """Manages WebSocket connections for WebSSH sessions."""

    def __init__(self):
        self._sessions: Dict[str, WebSSHSession] = {}
        self._user_sessions: Dict[int, Set[str]] = {}

    def add_session(self, session: WebSSHSession):
        self._sessions[session.session_id] = session
        if session.user_id not in self._user_sessions:
            self._user_sessions[session.user_id] = set()
        self._user_sessions[session.user_id].add(session.session_id)

    def remove_session(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            session.is_alive = False
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id].discard(session_id)

    def get_session(self, session_id: str) -> Optional[WebSSHSession]:
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: int) -> list[WebSSHSession]:
        session_ids = self._user_sessions.get(user_id, set())
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def get_user_session_count(self, user_id: int) -> int:
        return len(self._user_sessions.get(user_id, set()))

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def broadcast_to_user(self, user_id: int, message: dict):
        sessions = self.get_user_sessions(user_id)
        for session in sessions:
            try:
                await session.websocket.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()

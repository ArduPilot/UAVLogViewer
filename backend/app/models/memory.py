from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SessionData:
    created_at_epoch_s: float
    summary: Dict[str, Any]
    signals: Optional[Dict[str, Any]] = None
    history: list[Dict[str, Any]] = field(default_factory=list)


class MemoryStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionData] = {}

    def create_or_get(self, client_session_id: Optional[str], summary: Dict[str, Any], signals: Optional[Dict[str, Any]]) -> str:
        if client_session_id and client_session_id in self._sessions:
            # Update summary/signals if provided again
            data = self._sessions[client_session_id]
            data.summary = summary or data.summary
            if signals is not None:
                data.signals = signals
            return client_session_id

        session_id = client_session_id or str(uuid.uuid4())
        self._sessions[session_id] = SessionData(
            created_at_epoch_s=time.time(),
            summary=summary,
            signals=signals,
        )
        return session_id

    def get(self, session_id: str) -> Optional[SessionData]:
        return self._sessions.get(session_id)


memory_store = MemoryStore()



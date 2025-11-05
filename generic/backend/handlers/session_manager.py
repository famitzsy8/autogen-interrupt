"""
Session Manager for handling multi-tab WebSocket connections.

Each session represents a single conversation that can be accessed
from multiple tabs/connections simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set
from dataclasses import dataclass, field

from starlette.websockets import WebSocket

from handlers.state_manager import StateManager
from factory.team_factory import AgentTeamContext

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """
    Represents a single conversation session that can have multiple WebSocket connections.
    """
    session_id: str
    state_manager: StateManager
    agent_team_context: AgentTeamContext | None = None
    websockets: Set[WebSocket] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def add_websocket(self, ws: WebSocket) -> None:
        """Add a WebSocket connection to this session."""
        self.websockets.add(ws)
        self.last_activity = datetime.now()
        logger.info(f"Session {self.session_id}: Added WebSocket. Total connections: {len(self.websockets)}")

    def remove_websocket(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from this session."""
        self.websockets.discard(ws)
        self.last_activity = datetime.now()
        logger.info(f"Session {self.session_id}: Removed WebSocket. Remaining connections: {len(self.websockets)}")

    def has_connections(self) -> bool:
        """Check if session has any active WebSocket connections."""
        return len(self.websockets) > 0


class SessionManager:
    """
    Manages all active sessions and their WebSocket connections.

    Features:
    - Multiple tabs can connect to the same session
    - Agent team is shared across all connections in a session
    - State is preserved even when all connections close (for a grace period)
    """

    def __init__(self) -> None:
        self.sessions: Dict[str, Session] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._session_timeout_seconds = 3600  # 1 hour
        logger.info("SessionManager initialized")

    def get_or_create_session(
        self,
        session_id: str,
        state_file_path: str
    ) -> Session:
        """
        Get existing session or create a new one.

        Args:
            session_id: Unique identifier for the session
            state_file_path: Path where this session's state should be stored

        Returns:
            Session object
        """
        if session_id in self.sessions:
            logger.info(f"Retrieving existing session: {session_id}")
            return self.sessions[session_id]

        logger.info(f"Creating new session: {session_id}")
        state_manager = StateManager(file_path=state_file_path)
        session = Session(
            session_id=session_id,
            state_manager=state_manager
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get an existing session, or None if it doesn't exist."""
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove a session and clean up its resources."""
        if session_id in self.sessions:
            logger.info(f"Removing session: {session_id}")
            session = self.sessions[session_id]

            # Close all WebSocket connections
            for ws in list(session.websockets):
                asyncio.create_task(self._close_websocket_safely(ws))

            del self.sessions[session_id]

    async def _close_websocket_safely(self, ws: WebSocket) -> None:
        """Safely close a WebSocket connection."""
        try:
            await ws.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket: {e}")

    def get_session_count(self) -> int:
        """Get the total number of active sessions."""
        return len(self.sessions)

    def get_total_connections(self) -> int:
        """Get the total number of WebSocket connections across all sessions."""
        return sum(len(session.websockets) for session in self.sessions.values())

    async def broadcast_to_session(
        self,
        session_id: str,
        message: str,
        exclude: WebSocket | None = None
    ) -> None:
        """
        Broadcast a message to all WebSocket connections in a session.

        Args:
            session_id: Session to broadcast to
            message: Message to send (JSON string)
            exclude: Optional WebSocket to exclude from broadcast
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot broadcast to non-existent session: {session_id}")
            return

        # Send to all connections except the excluded one
        for ws in list(session.websockets):
            if ws != exclude:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket in session {session_id}: {e}")
                    # Remove dead connection
                    session.remove_websocket(ws)

    def cleanup_inactive_sessions(self) -> None:
        """
        Remove sessions that have no connections and haven't been active recently.
        This is called periodically to prevent memory leaks.
        """
        now = datetime.now()
        sessions_to_remove = []

        for session_id, session in self.sessions.items():
            # Remove sessions with no connections that have been inactive
            if not session.has_connections():
                inactive_seconds = (now - session.last_activity).total_seconds()
                if inactive_seconds > self._session_timeout_seconds:
                    sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            logger.info(f"Cleaning up inactive session: {session_id}")
            self.remove_session(session_id)


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

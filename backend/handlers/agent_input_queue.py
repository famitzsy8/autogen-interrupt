"""Input queue for handling user input via WebSocket."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional

from autogen_core import CancellationToken

if TYPE_CHECKING:
    from websocket_handler import WebSocketHandler

logger = logging.getLogger(__name__)


class AgentInputQueue:

    def __init__(self) -> None:
        self.pending_requests: dict[str, tuple[asyncio.Future[str], str, str]] = {}
        self.websocket_handler: Optional[WebSocketHandler] = None

    async def get_input(
        self,
        prompt: str,
        agent_name: str,
        cancellation_token: Optional[CancellationToken] = None,
        feedback_context: dict[str, Any] | None = None,
    ) -> str:
        if not self.websocket_handler:
            raise RuntimeError("WebSocketHandler is not set for AgentInputQueue.")

        request_id = str(uuid.uuid4())
        future: asyncio.Future[str] = asyncio.Future()

        self.pending_requests[request_id] = (future, prompt, agent_name)

        if feedback_context is None and self.websocket_handler and self.websocket_handler.session:
            session = self.websocket_handler.session

            if session.agent_team_context and session.agent_team_context.team:
                team = session.agent_team_context.team
                if hasattr(team, '_feedback_context'):
                    if team._feedback_context:
                        feedback_context = team._feedback_context
                        team._feedback_context = None

        await self.websocket_handler.send_agent_input_request(
            request_id, prompt, agent_name, feedback_context
        )

        if cancellation_token is not None:
            cancellation_token.link_future(future)

        try:
            return await future
        except asyncio.CancelledError:
            self.pending_requests.pop(request_id, None)
            raise

    def provide_input(self, request_id: str, user_input: str) -> bool:
        if request_id in self.pending_requests:
            future, _, agent_name = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_result(user_input)
                return True
        return False

    def cancel_all_pending(self) -> None:
        if not self.pending_requests:
            return

        for request_id, (future, _, agent_name) in list(self.pending_requests.items()):
            if not future.done():
                try:
                    future.cancel()
                except Exception as e:
                    logger.error(f"Error cancelling future {request_id[:8]} for {agent_name}: {e}")

        self.pending_requests.clear()

    def has_pending_requests(self) -> bool:
        return len(self.pending_requests) > 0

    def get_pending_count(self) -> int:
        return len(self.pending_requests)

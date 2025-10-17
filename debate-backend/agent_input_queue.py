"""Async input queue for agents requiring human input via WebSocket.

This module provides a generic mechanism for any agent (e.g., UserProxyAgent) to request
human input through WebSocket connections instead of stdin. The naming is role-agnostic
to support any agent type that needs human interaction.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Optional

from autogen_core import CancellationToken

if TYPE_CHECKING:
    from websocket_handler import WebSocketHandler


class AgentInputQueue:
    """
    Handles agent input requests via WebSocket instead of stdin.

    This class provides a bridge between agents that need human input (like UserProxyAgent)
    and the WebSocket connection to the frontend. It's designed to be role-agnostic and
    can support any agent type.

    Flow:
    1. Agent calls get_input(prompt) when it needs human response
    2. Queue stores a Future for the request
    3. Notifies frontend via WebSocket (through WebSocketHandler)
    4. Waits for frontend to provide response
    5. Returns response to the agent

    Attributes:
        pending_requests: Map of request_id to (Future, prompt, agent_name)
        websocket_handler: Reference to WebSocketHandler for sending messages
    """

    def __init__(self) -> None:
        """Initialize the agent input queue."""
        self.pending_requests: dict[str, tuple[asyncio.Future[str], str, str]] = {}
        self.websocket_handler: Optional[WebSocketHandler] = None

    async def get_input(
        self,
        prompt: str,
        cancellation_token: Optional[CancellationToken] = None,
        agent_name: str = "Agent"
    ) -> str:
        """
        Request human input for an agent.

        This is the function that gets passed to agents (like UserProxyAgent) as their
        input_func parameter. It replaces the default stdin input() with WebSocket-based
        communication.

        Args:
            prompt: The prompt/question to display to the human user
            cancellation_token: Optional cancellation token for timeout support
            agent_name: Name of the agent requesting input (for context)

        Returns:
            The human user's input string

        Raises:
            asyncio.CancelledError: If the request is cancelled
            RuntimeError: If WebSocket handler is not set
        """
        if not self.websocket_handler:
            raise RuntimeError("WebSocket handler not initialized for agent input queue")

        request_id = str(uuid.uuid4())
        future: asyncio.Future[str] = asyncio.Future()

        # Store the request with prompt and agent name for context
        self.pending_requests[request_id] = (future, prompt, agent_name)

        # Notify frontend via WebSocket
        await self.websocket_handler.send_agent_input_request(request_id, prompt, agent_name)

        # Link cancellation token for timeout support
        if cancellation_token is not None:
            cancellation_token.link_future(future)

        # Wait for frontend to respond
        try:
            return await future
        except asyncio.CancelledError:
            # Clean up if cancelled
            self.pending_requests.pop(request_id, None)
            raise

    def provide_input(self, request_id: str, user_input: str) -> bool:
        """
        Provide the human user's response to a pending input request.

        Called by WebSocketHandler when the frontend sends the user's response.

        Args:
            request_id: The request ID from get_input()
            user_input: The human user's response string

        Returns:
            True if request was found and fulfilled, False if request_id not found
        """
        if request_id in self.pending_requests:
            future, prompt, agent_name = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_result(user_input)
                print(f"✓ Provided input for {agent_name} request: {request_id}")
                return True
            else:
                print(f"⚠️ Future already done for request: {request_id}")
        else:
            print(f"⚠️ No pending request found for: {request_id}")
        return False

    def cancel_all_pending(self) -> None:
        """
        Cancel all pending input requests.

        Called during cleanup (e.g., WebSocket disconnect) to ensure no requests
        are left hanging.
        """
        for request_id, (future, prompt, agent_name) in list(self.pending_requests.items()):
            if not future.done():
                future.cancel()
                print(f"✗ Cancelled pending input request for {agent_name}: {request_id}")
        self.pending_requests.clear()

    def has_pending_requests(self) -> bool:
        """Check if there are any pending input requests."""
        return len(self.pending_requests) > 0

    def get_pending_count(self) -> int:
        """Get the number of pending input requests."""
        return len(self.pending_requests)

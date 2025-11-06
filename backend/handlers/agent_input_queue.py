# This is an Input Queue that handles the input listening via the WebSocket server

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Optional

from autogen_core import CancellationToken 

if TYPE_CHECKING:
    from websocket_handler import WebSocketHandler

class AgentInputQueue:

    def __init__(self) -> None:
        self.pending_requests: dict[str, tuple[asyncio.Future[str], str, str]] = {}
        self.websocket_handler: Optional[WebSocketHandler] = None
    
    async def get_input(
        self,
        prompt: str,
        agent_name: str,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> str:
        
        if not self.websocket_handler:
            raise RuntimeError("WebSocketHandler is not set for AgentInputQueue.")
        
        request_id = str(uuid.uuid4())
        future: asyncio.Future[str] = asyncio.Future()

        self.pending_requests[request_id] = (future, prompt, agent_name)

        await self.websocket_handler.send_agent_input_request(request_id, prompt, agent_name)

        if cancellation_token is not None:
            cancellation_token.link_future(future)
        
        # Then we wait for the user in the frontend to respond...
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
                return True # Sucessfully provided input
            else:
                print(f"Future for request_id {request_id} is already done.")
        else:
            print(f"No pending request found for request_id {request_id}.")
        return False

    def cancel_all_pending(self) -> None:

        for request_id, (future, _, _) in list(self.pending_requests.items()):
            if not future.done():
                future.cancel()
        self.pending_requests.clear()
    
    def has_pending_requests(self) -> bool:
        return len(self.pending_requests) > 0

    def get_pending_count(self) -> int:
        return len(self.pending_requests)
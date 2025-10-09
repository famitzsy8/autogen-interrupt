from typing import AsyncGenerator, Sequence

from autogen_core import CancellationToken

from ..base import Response, TaskResult
from ..messages import BaseAgentEvent, BaseChatMessage, TextMessage
from ..teams._group_chat._base_group_chat import BaseGroupChat
from ._base_chat_agent import BaseChatAgent


class UserControlAgent(BaseChatAgent):
    """Agent for programmatic user control over a running team.

    This agent emits no model calls; it's a thin wrapper exposing helper methods
    to send interrupts and user-directed messages to a `BaseGroupChat`.
    """

    def __init__(self, name: str, description: str = "A user control agent") -> None:
        super().__init__(name=name, description=description)

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        # Control agent does not transform messages; it is invoked via helper methods.
        return Response(chat_message=TextMessage(content="", source=self.name))

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        yield Response(chat_message=TextMessage(content="", source=self.name))

    async def interrupt(self, team: BaseGroupChat) -> None:
        await team.interrupt()

    async def send(self, team: BaseGroupChat, msg: str, agent: str) -> TaskResult:
        return await team.send_user_message(TextMessage(content=msg, source=self.name), agent)

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset method - no-op for control agent as it has no state to reset."""
        pass



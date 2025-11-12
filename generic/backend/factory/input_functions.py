from typing import Optional
from autogen_core import CancellationToken
from handlers.agent_input_queue import AgentInputQueue


async def queue_based_input(
    agent_input_queue: AgentInputQueue,
    agent_name: str,
    prompt: str,
    cancellation_token: Optional[CancellationToken] = None,
) -> str:
    # Input function template - gets wrapped in closure in team_factory.py
    # to bind agent_input_queue and agent_name at agent creation time
    return await agent_input_queue.get_input(
        prompt=prompt,
        cancellation_token=cancellation_token,
        agent_name=agent_name,
    )

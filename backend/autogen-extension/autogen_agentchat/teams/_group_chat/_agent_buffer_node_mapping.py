"""
Agent Buffer Trim Translation Module

This module converts the GroupChatManager's trim_up value (which counts ALL nodes
including tool call nodes) to per-agent trim_up values (which count only message nodes
that exist in each agent's buffer).

## The Problem

1. GroupChatManager trim_up counts:
   - Message nodes (BaseChatMessage)
   - Tool call nodes (ToolCallRequestEvent + ToolCallExecutionEvent pair = 1 node)

2. Agent buffers only contain:
   - BaseChatMessage entries (no tool events)

3. Agent buffers are CLEARED after the agent responds, so each agent has a different
   buffer size depending on when they last spoke.

## Solution

For each agent, we need to:
1. Find where the agent last sent a message (their buffer was cleared at that point)
2. Count only the BaseChatMessage entries in the trim range that are AFTER the agent's
   last message (these are the only ones in the agent's buffer)

## Example

Message thread: [Task, A_msg, B_msg, C_msg, D_msg]
                  0      1      2      3      4

After D just spoke, agent buffer states:
- Agent A: buffer = [B_msg, C_msg, D_msg]  (3 messages since A spoke at index 1)
- Agent B: buffer = [C_msg, D_msg]          (2 messages since B spoke at index 2)
- Agent C: buffer = [D_msg]                 (1 message since C spoke at index 3)
- Agent D: buffer = []                      (just cleared after responding at index 4)

User sends trim_up=2 (remove C_msg and D_msg, indices 3-4)

Per-agent trim values:
- Agent A: trim 2 (both C_msg and D_msg are in A's buffer)
- Agent B: trim 2 (both C_msg and D_msg are in B's buffer)
- Agent C: trim 1 (only D_msg is in C's buffer, C_msg is C's own message)
- Agent D: trim 0 (D's buffer is empty)
"""

from typing import Sequence
from ...messages import BaseAgentEvent, BaseChatMessage, ToolCallRequestEvent, ToolCallExecutionEvent


def _find_last_message_index_from_agent(
    message_thread: Sequence[BaseAgentEvent | BaseChatMessage],
    agent_name: str
) -> int:
    """
    Find the index of the last message sent by a specific agent.

    Args:
        message_thread: The current flat message thread from the manager
        agent_name: The name of the agent to find

    Returns:
        Index of the agent's last message, or -1 if agent hasn't sent any message
    """
    for i in range(len(message_thread) - 1, -1, -1):
        msg = message_thread[i]
        if isinstance(msg, BaseChatMessage) and msg.source == agent_name:
            return i
    return -1


def convert_manager_trim_to_agent_trim(
    message_thread: Sequence[BaseAgentEvent | BaseChatMessage],
    manager_trim_up: int,
    agent_name: str
) -> int:
    """
    Convert GroupChatManager's trim_up value to a specific agent's trim_up value.

    The manager counts ALL nodes (messages + tool calls).
    Each agent's buffer only contains messages received AFTER they last spoke.
    This function computes how many messages in the trim range are actually in
    the specified agent's buffer.

    Args:
        message_thread: The current flat message thread from the manager
        manager_trim_up: Number of ALL nodes (logical units) to remove
        agent_name: The name of the agent to compute trim for

    Returns:
        Number of message nodes to remove from this agent's buffer

    Raises:
        ValueError: If manager_trim_up is invalid

    Example:
        >>> # Thread: [Task, A_msg, B_msg, C_msg, D_msg]
        >>> # manager_trim_up=2 (remove C_msg and D_msg)
        >>> # Agent C's buffer only has [D_msg] (C_msg is C's own message)
        >>> agent_trim = convert_manager_trim_to_agent_trim(thread, 2, "C")
        >>> assert agent_trim == 1
    """
    if manager_trim_up < 0:
        raise ValueError(f"manager_trim_up must be non-negative, got {manager_trim_up}")

    if manager_trim_up == 0:
        return 0

    if len(message_thread) == 0:
        raise ValueError("Cannot trim from empty message thread")

    # Find where this agent last spoke (their buffer was cleared at that point)
    last_agent_msg_idx = _find_last_message_index_from_agent(message_thread, agent_name)

    # If agent never spoke, their buffer contains all messages from the start
    # (after the initial task message, which is index 0)
    buffer_start_idx = last_agent_msg_idx + 1 if last_agent_msg_idx >= 0 else 0

    # Walk backwards through the thread to find the trim range
    # We need to count nodes until we've counted manager_trim_up nodes
    agent_trim_count = 0
    nodes_counted = 0
    i = len(message_thread) - 1

    while i >= 0 and nodes_counted < manager_trim_up:
        current_msg = message_thread[i]

        # Check if this is a ToolCallExecutionEvent
        if isinstance(current_msg, ToolCallExecutionEvent):
            # A ToolCallExecutionEvent + ToolCallRequestEvent = 1 tool call node
            # We count this as a node but NOT as a message node for agents
            i -= 1

            # Find the matching ToolCallRequestEvent
            if i >= 0 and isinstance(message_thread[i], ToolCallRequestEvent):
                i -= 1
                nodes_counted += 1
                # Do NOT increment agent_trim_count (tool calls don't count for agents)
            else:
                raise ValueError(
                    f"Found ToolCallExecutionEvent at index {i+1} without matching "
                    f"ToolCallRequestEvent before it. Message thread may be corrupted."
                )
        else:
            # Any other message type = 1 node
            if isinstance(current_msg, BaseChatMessage):
                # Only count this message for the agent if it's AFTER their last message
                # (i.e., it's actually in their buffer)
                if i >= buffer_start_idx:
                    agent_trim_count += 1
            nodes_counted += 1
            i -= 1

    if nodes_counted < manager_trim_up:
        raise ValueError(
            f"Cannot trim {manager_trim_up} nodes: only {nodes_counted} nodes available in message thread"
        )

    return agent_trim_count

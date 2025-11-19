"""
Agent Buffer Trim Translation Module

This module converts the GroupChatManager's trim_up value (which counts ALL nodes
including tool call nodes) to the agents' trim_up value (which counts only message nodes).

## The Problem

GroupChatManager trim_up counts:
- Message nodes (BaseChatMessage)
- Tool call nodes (ToolCallRequestEvent + ToolCallExecutionEvent pair = 1 node)

Agent buffers only contain:
- BaseChatMessage entries (no tool events)

So when we need to tell agents to trim, we must convert:
- Manager trim_up=3 (e.g., 2 messages + 1 tool sequence)
- Agent trim_up=2 (only the 2 messages, skip the tool sequence)

## Solution

Walk backwards through the message thread, counting only the BaseChatMessage entries
we encounter, until we've counted trim_up nodes. Return the count of BaseChatMessage
entries found.

## Example

Message thread (last 4 entries): [TextMessage, ToolCallRequest, ToolCallExecution, TextMessage]
Logical nodes (last 3): [Message, ToolCall, Message]

Manager trim_up=3 → remove last 3 nodes
Walk backwards:
- Entry 3 (TextMessage) = node 1, is_chat_message=True, agent_trim=1
- Entry 2 (ToolCallExecution) = part of node 2, is_chat_message=False
- Entry 1 (ToolCallRequest) = node 2, is_chat_message=False
- Entry 0 (TextMessage) = node 3, is_chat_message=True, agent_trim=2

Result: agent trim_up=2 (only the 2 message nodes)
"""

from typing import Sequence
from ...messages import BaseAgentEvent, BaseChatMessage, ToolCallRequestEvent, ToolCallExecutionEvent


def convert_manager_trim_to_agent_trim(
    message_thread: Sequence[BaseAgentEvent | BaseChatMessage],
    manager_trim_up: int
) -> int:
    """
    Convert GroupChatManager's trim_up value to the agents' trim_up value.

    The manager counts ALL nodes (messages + tool calls).
    Agents only see messages, so we need to count only BaseChatMessage nodes.

    Args:
        message_thread: The current flat message thread from the manager
        manager_trim_up: Number of ALL nodes (logical units) to remove

    Returns:
        Number of message nodes (not tool call nodes) to remove from agent buffers

    Raises:
        ValueError: If manager_trim_up is invalid

    Example:
        >>> # Thread (last 5 entries): [TextMsg, ToolReq, ToolExec, TextMsg, TextMsg]
        >>> # Nodes (last 3): [Message, ToolCall, Message]
        >>> # manager_trim_up=3 → agent_trim_up=2 (skip the tool call)
        >>> agent_trim = convert_manager_trim_to_agent_trim(thread, manager_trim_up=3)
        >>> assert agent_trim == 2
    """
    if manager_trim_up < 0:
        raise ValueError(f"manager_trim_up must be non-negative, got {manager_trim_up}")

    if manager_trim_up == 0:
        return 0

    if len(message_thread) == 0:
        raise ValueError("Cannot trim from empty message thread")

    # Walk backwards through the thread, counting only BaseChatMessage nodes
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
            # Any other message type = 1 node, and it's a message node for agents
            if isinstance(current_msg, BaseChatMessage):
                agent_trim_count += 1  # Count this for agents
            # (Other BaseAgentEvent types aren't in thread, so we don't worry about them)
            nodes_counted += 1
            i -= 1

    if nodes_counted < manager_trim_up:
        raise ValueError(
            f"Cannot trim {manager_trim_up} nodes: only {nodes_counted} nodes available in message thread"
        )

    return agent_trim_count

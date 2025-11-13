"""
Node-to-Message Mapping Module

This module defines the relationship between frontend tree nodes and backend message thread entries.

## Architectural Context

The frontend displays a tree structure where each node represents a logical unit of conversation:
- 1 node = 1 message (text, user input, etc.)
- 1 node = 1 tool call sequence (request + execution grouped together)

The backend message thread, however, is a flat list that includes:
- 1 entry per BaseChatMessage (UserMessage, TextMessage, etc.)
- 1 entry per BaseAgentEvent (ToolCallRequestEvent, ToolCallExecutionEvent, etc.)

This creates a structural mismatch: a single tool call node in the frontend corresponds to
2 entries in the message thread (ToolCallRequestEvent + ToolCallExecutionEvent).

## Usage

When branching/trimming the conversation:
1. Frontend calculates trim_up = number of nodes to remove
2. Backend receives trim_up value
3. Backend must convert trim_up (node count) → actual message count using this module
4. Backend trims the message thread by the calculated message count

## Example

If a user interrupts at a node that's 3 levels up:
- trim_up = 3 (nodes to remove)
- We scan the last 3 "logical units" in the thread
- If they're: [message, message, tool_sequence], that's 4 actual entries
- We trim: message_thread = message_thread[:-4]
"""

from typing import Sequence
from ...messages import BaseAgentEvent, BaseChatMessage, ToolCallRequestEvent, ToolCallExecutionEvent


def count_messages_for_node_trim(
    message_thread: Sequence[BaseAgentEvent | BaseChatMessage],
    trim_up: int
) -> int:
    """
    Convert a node-based trim count to actual message thread entries to trim.

    Args:
        message_thread: The current flat message thread containing all entries
        trim_up: Number of nodes (logical units) to remove from the end

    Returns:
        Number of actual message thread entries to remove

    Raises:
        ValueError: If trim_up is invalid or exceeds available nodes

    Example:
        >>> # Thread: [TextMessage, ToolCallRequestEvent, ToolCallExecutionEvent, TextMessage]
        >>> # trim_up=2 means remove last 2 nodes: (tool_sequence, message)
        >>> # That's 3 actual entries: ToolCallRequestEvent + ToolCallExecutionEvent + TextMessage
        >>> messages_to_trim = count_messages_for_node_trim(thread, trim_up=2)
        >>> assert messages_to_trim == 3
    """
    if trim_up < 0:
        raise ValueError(f"trim_up must be non-negative, got {trim_up}")

    if trim_up == 0:
        return 0

    if len(message_thread) == 0:
        raise ValueError("Cannot trim from empty message thread")

    # Walk backwards through the thread, counting nodes until we've counted trim_up nodes
    message_count = 0
    nodes_counted = 0
    i = len(message_thread) - 1

    while i >= 0 and nodes_counted < trim_up:
        current_msg = message_thread[i]

        # Check if this is a ToolCallExecutionEvent
        if isinstance(current_msg, ToolCallExecutionEvent):
            # A ToolCallExecutionEvent + ToolCallRequestEvent = 1 node
            # We need to skip back to find the matching request
            message_count += 1  # Count this execution event
            i -= 1

            # Find the matching ToolCallRequestEvent
            if i >= 0 and isinstance(message_thread[i], ToolCallRequestEvent):
                message_count += 1  # Count the request event
                i -= 1
                nodes_counted += 1
            else:
                raise ValueError(
                    f"Found ToolCallExecutionEvent at index {i+1} without matching "
                    f"ToolCallRequestEvent before it. Message thread may be corrupted."
                )
        else:
            # Any other message type (BaseChatMessage or other BaseAgentEvent) = 1 node = 1 entry
            message_count += 1
            nodes_counted += 1
            i -= 1

    if nodes_counted < trim_up:
        raise ValueError(
            f"Cannot trim {trim_up} nodes: only {nodes_counted} nodes available in message thread"
        )

    return message_count


def analyze_thread_structure(message_thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> dict:
    """
    Analyze the structure of the message thread and return statistics.

    Useful for debugging and understanding the current state of the thread.

    Returns:
        Dictionary with keys:
        - total_messages: Total entries in thread
        - node_count: Number of logical nodes (accounting for tool sequences)
        - chat_messages: Count of BaseChatMessage entries
        - tool_call_requests: Count of ToolCallRequestEvent entries
        - tool_call_executions: Count of ToolCallExecutionEvent entries
        - other_events: Count of other BaseAgentEvent entries
    """
    stats = {
        "total_messages": len(message_thread),
        "node_count": 0,
        "chat_messages": 0,
        "tool_call_requests": 0,
        "tool_call_executions": 0,
        "other_events": 0,
    }

    i = 0
    while i < len(message_thread):
        msg = message_thread[i]

        if isinstance(msg, ToolCallRequestEvent):
            stats["tool_call_requests"] += 1
            # Check if next is execution
            if i + 1 < len(message_thread) and isinstance(message_thread[i + 1], ToolCallExecutionEvent):
                stats["tool_call_executions"] += 1
                stats["node_count"] += 1  # Tool pair = 1 node
                i += 2  # Skip both request and execution
            else:
                # Request without execution = 1 node
                stats["node_count"] += 1
                i += 1
        elif isinstance(msg, ToolCallExecutionEvent):
            # Execution without preceding request (shouldn't happen, but handle it)
            stats["tool_call_executions"] += 1
            stats["node_count"] += 1
            i += 1
        elif isinstance(msg, BaseChatMessage):
            stats["chat_messages"] += 1
            stats["node_count"] += 1
            i += 1
        else:
            # Other BaseAgentEvent types
            stats["other_events"] += 1
            stats["node_count"] += 1
            i += 1

    return stats

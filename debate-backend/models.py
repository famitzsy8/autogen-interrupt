"""Pydantic models for WebSocket messages and conversation tree structures."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """WebSocket message types for client-server communication."""

    AGENT_MESSAGE = "agent_message"
    USER_INTERRUPT = "user_interrupt"
    USER_DIRECTED_MESSAGE = "user_directed_message"
    INTERRUPT_ACKNOWLEDGED = "interrupt_acknowledged"
    STREAM_END = "stream_end"
    ERROR = "error"
    TREE_UPDATE = "tree_update"


class AgentMessage(BaseModel):
    """Message sent from an agent during the debate conversation."""

    type: Literal[MessageType.AGENT_MESSAGE] = MessageType.AGENT_MESSAGE
    agent_name: str = Field(..., description="Name of the agent sending the message")
    content: str = Field(..., description="Message content from the agent")
    timestamp: datetime = Field(default_factory=datetime.now)
    node_id: str = Field(..., description="Unique identifier for this message node in the tree")

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        """Ensure agent name is not empty."""
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure message content is not empty."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v


class UserInterrupt(BaseModel):
    """Request from client to interrupt the agent conversation stream."""

    type: Literal[MessageType.USER_INTERRUPT] = MessageType.USER_INTERRUPT
    timestamp: datetime = Field(default_factory=datetime.now)


class UserDirectedMessage(BaseModel):
    """Message from user directed to a specific agent with optional thread trimming."""

    type: Literal[MessageType.USER_DIRECTED_MESSAGE] = MessageType.USER_DIRECTED_MESSAGE
    content: str = Field(..., description="User's message content")
    target_agent: str = Field(..., description="Name of agent to receive the message")
    trim_count: int = Field(
        default=0,
        ge=0,
        description="Number of messages to traverse up the tree before branching (0 = branch from current)",
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure message content is not empty."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v

    @field_validator("target_agent")
    @classmethod
    def validate_target_agent(cls, v: str) -> str:
        """Ensure target agent name is not empty."""
        if not v or not v.strip():
            raise ValueError("target_agent cannot be empty")
        return v.strip()


class InterruptAcknowledged(BaseModel):
    """Acknowledgment that the interrupt was successful and ready for user input."""

    type: Literal[MessageType.INTERRUPT_ACKNOWLEDGED] = MessageType.INTERRUPT_ACKNOWLEDGED
    message: str = "Conversation interrupted. Ready for user input."
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamEnd(BaseModel):
    """Notification that the agent conversation stream has ended."""

    type: Literal[MessageType.STREAM_END] = MessageType.STREAM_END
    reason: str = Field(..., description="Reason for stream termination")
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorMessage(BaseModel):
    """Error notification sent to client."""

    type: Literal[MessageType.ERROR] = MessageType.ERROR
    error_code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(default_factory=datetime.now)


class TreeNode(BaseModel):
    """A node in the conversation tree representing a single message."""

    id: str = Field(..., description="Unique node identifier")
    agent_name: str = Field(..., description="Name of agent who sent this message")
    message: str = Field(..., description="Message content")
    parent: str | None = Field(default=None, description="ID of parent node (None for root)")
    children: list[TreeNode] = Field(default_factory=list, description="Child nodes")
    is_active: bool = Field(
        default=True, description="False for nodes in abandoned branches (reduced opacity)"
    )
    branch_id: str = Field(..., description="Identifier for which branch this node belongs to")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure node ID is not empty."""
        if not v or not v.strip():
            raise ValueError("id cannot be empty")
        return v.strip()

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        """Ensure agent name is not empty."""
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()

    model_config = {"from_attributes": True}


class TreeUpdate(BaseModel):
    """Complete tree structure update sent to client."""

    type: Literal[MessageType.TREE_UPDATE] = MessageType.TREE_UPDATE
    root: TreeNode = Field(..., description="Root node of the conversation tree")
    current_branch_id: str = Field(..., description="ID of the currently active branch")
    timestamp: datetime = Field(default_factory=datetime.now)

# This file contains all the Pydantic models for the WebSocket messages
# we recieve and send from/to the frontend.

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

class MessageType(str, Enum):

    # WebSocket message types (equal in frontend src/types/index.ts)
    AGENT_TEAM_NAMES = 'agent_team_names'
    PARTICIPANT_NAMES = 'participant_names'
    RUN_CONFIG = 'RUN_CONFIG'
    START_RUN = 'start_run'
    AGENT_MESSAGE = 'agent_message'
    USER_INTERRUPT = 'user_interrupt'
    USER_DIRECTED_MESSAGE = 'user_directed_message'
    INTERRUPT_ACKNOWLEDGED = 'interrupt_acknowledged'
    STREAM_END = 'stream_end'
    ERROR = 'error'
    TREE_UPDATE = 'tree_update'
    AGENT_INPUT_REQUEST = 'agent_input_request'
    HUMAN_INPUT_RESPONSE = 'human_input_response'
    TOOL_CALL = 'tool_call'
    TOOL_EXECUTION = 'tool_execution'


class AgentTeamNames(BaseModel):
    # Agent team names fixed in the YAML file in the backend that we set here in the frontend
    type: Literal[MessageType.AGENT_TEAM_NAMES] = MessageType.AGENT_TEAM_NAMES
    agent_team_names: list[str] = Field(..., description="List of agent team names")

    @field_validator("agent_team_names")
    @classmethod
    def validate_agent_team_names(cls, v: list[str]) -> list[str]:
        # Agent team names list must not be empty
        if not v:
            raise ValueError("agent_team_names cannot be empty")
        return v

class ParticipantNames(BaseModel):
    # Individual agent participant names in the initialized team
    type: Literal[MessageType.PARTICIPANT_NAMES] = MessageType.PARTICIPANT_NAMES
    participant_names: list[str] = Field(..., description="List of agent participant names")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("participant_names")
    @classmethod
    def validate_participant_names(cls, v: list[str]) -> list[str]:
        # Participant names list must not be empty
        if not v:
            raise ValueError("participant_names cannot be empty")
        return v

class AgentMessage(BaseModel):

    # This is the message that an agent generated in the team conversation

    type: Literal[MessageType.AGENT_MESSAGE] = MessageType.AGENT_MESSAGE # to enforce strict type constraints for sync in frontend

    agent_name: str = Field(..., description="Name of the agent sending the message")
    content: str = Field(..., description="Message content from the agent")
    summary: str = Field(..., description="AI-generated summary of the message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    node_id: str = Field(..., description="Unique identifier for this message node in the tree")

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        # Agent name must not be empty
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        # Content must not be empty
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()

    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        # Node ID must not be empty
        if not v or not v.strip():
            raise ValueError("node_id cannot be empty")
        return v.strip()


class UserInterrupt(BaseModel):
    # A user-sent interrupt request to interrupt the agent conversation stream.

    type: Literal[MessageType.USER_INTERRUPT] = MessageType.USER_INTERRUPT
    timestamp: datetime = Field(default_factory=datetime.now)

class UserDirectedMessage(BaseModel):
    # Message sent from the user from a specific point in the conversation tree (on the current branch only!) to a specific agent.
    type: Literal[MessageType.USER_DIRECTED_MESSAGE] = MessageType.USER_DIRECTED_MESSAGE

    content: str = Field(..., description="The message content from the human user")
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
        # Content must not be empty
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v

    @field_validator("target_agent")
    @classmethod
    def validate_target_agent(cls, v: str) -> str:
        # Target agent name must not be empty
        if not v or not v.strip():
            raise ValueError("target_agent cannot be empty")
        return v.strip()


class InterruptAcknowledged(BaseModel):
    # Acknowledgment that the interrupt was successful and ready for user input.

    type: Literal[MessageType.INTERRUPT_ACKNOWLEDGED] = MessageType.INTERRUPT_ACKNOWLEDGED
    message: str = "Conversation interrupted. Ready for user input."
    timestamp: datetime = Field(default_factory=datetime.now)

class StreamEnd(BaseModel):
    # Notification that the agent conversation stream has ended.
    type: Literal[MessageType.STREAM_END] = MessageType.STREAM_END
    reason: str = Field(..., description="Reason for stream termination")
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorMessage(BaseModel):
    # Error notification sent to client.

    type: Literal[MessageType.ERROR] = MessageType.ERROR
    error_code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(default_factory=datetime.now)

class TreeNode(BaseModel):
    # A node in the conversation tree representing a single message.

    id: str = Field(..., description="Unique node message identifier")
    agent_name: str = Field(..., description="Name of the agent who sent this message")
    display_name: str = Field(..., description="Display name of the agent (human-readable)")
    message: str = Field(..., description="Message content")
    summary: str = Field(default="", description="AI-generated summary of the message content")
    parent: str | None = Field(default=None, description="ID of the parent node (None for root)")
    children: list[TreeNode] = Field(default_factory=list, description="Child nodes")

    is_active: bool = Field(
        default=True, description="False for nodes that are in non-active branches (reduced opacity)"
    )
    branch_id: str = Field(..., description="Identifier for which branch this node belongs to")
    timestamp: datetime = Field(default_factory=datetime.now)
    node_type: str = Field(
        default="message",
        description="Type of node: 'message' (counts in trim), 'tool_call' (doesn't count), 'tool_execution' (doesn't count)"
    )
    # don't know if we need gcm_count (GroupChatManager messages hidden under this node)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        # Node ID must not be empty
        if not v or not v.strip():
            raise ValueError("id cannot be empty")
        return v.strip()

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        # Agent name must not be empty
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()

    # model_config = {"from_attributes": True} --> don't know if we need this


class TreeUpdate(BaseModel):
    # Complete tree structure update sent to client.

    type: Literal[MessageType.TREE_UPDATE] = MessageType.TREE_UPDATE
    root: TreeNode = Field(..., description="Root node of the conversation tree")
    current_branch_id: str = Field(..., description="ID of the currently active branch")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("current_branch_id")
    @classmethod
    def validate_current_branch_id(cls, v: str) -> str:
        # Current branch ID must not be empty
        if not v or not v.strip():
            raise ValueError("current_branch_id cannot be empty")
        return v.strip()


class AgentInputRequest(BaseModel):
    # Request sent from backend to frontend when an agent needs human input.
    # This has to be used with a UserProxyAgent in the agent team, or an extension of it.

    type: Literal[MessageType.AGENT_INPUT_REQUEST] = MessageType.AGENT_INPUT_REQUEST

    request_id: str = Field(..., description="Unique identifier for this input request")
    prompt: str = Field(..., description="The question/prompt to display to the human user")
    agent_name: str = Field(..., description="Name of the agent requesting input")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, v: str) -> str:
        # Request ID must not be empty
        if not v or not v.strip():
            raise ValueError("request_id cannot be empty")
        return v.strip()

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        # Prompt must not be empty
        if not v or not v.strip():
            raise ValueError("prompt cannot be empty")
        return v

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        # Agent name must not be empty
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()


class HumanInputResponse(BaseModel):
    # Response sent from frontend to backend with the human user's input.
    # This is the user's response to an AgentInputRequest, providing the answer/approval that the agent was waiting for.

    type: Literal[MessageType.HUMAN_INPUT_RESPONSE] = MessageType.HUMAN_INPUT_RESPONSE
    request_id: str = Field(..., description="ID matching the original AgentInputRequest")
    user_input: str = Field(..., description="The human user's response to the prompt")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, v: str) -> str:
        # Request ID must not be empty
        if not v or not v.strip():
            raise ValueError("request_id cannot be empty")
        return v.strip()

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, v: str) -> str:
        # User input must not be empty
        if not v or not v.strip():
            raise ValueError("user_input cannot be empty")
        return v

class RunConfig(BaseModel):
    # Configuration of agent team: prompt to select next agent and initial task
    # Open to be expanded with more variables

    type: Literal[MessageType.START_RUN] = MessageType.START_RUN

    session_id: str = Field(..., description="Unique session ID for this conversation (enables multi-tab support)")

    initial_topic: str | None = Field(
        default=None,
        description="The task of the agent team (optional, uses backend default if not provided)",
    )
    selector_prompt: str | None = Field(
        default=None,
        description="Prompt to set the next agent selection policy in the agent team",
    )

    # Company-bill investigation parameters
    company_name: str | None = Field(
        default=None,
        description="Name of the company being investigated"
    )
    bill_name: str | None = Field(
        default=None,
        description="Bill identifier (e.g., S.1593)"
    )
    congress: str | None = Field(
        default=None,
        description="Congress number (e.g., 116th, 117th)"
    )

    timestamp: datetime = Field(default_factory=datetime.now)

class ToolCallInfo(BaseModel): # corresponds to ToolCallRequestEvent in autogen
    # Information about a single tool/function call.

    id: str = Field(..., description="Unique identifier for this tool call")
    name: str = Field(..., description="Name of the tool/function being called")
    arguments: str = Field(..., description="JSON string of arguments passed to the tool")

class ToolCall(BaseModel):
    # Message sent when an agent requests tool/function calls. 
    # Can be mulitiple tool calls in one message.

    type: Literal[MessageType.TOOL_CALL] = MessageType.TOOL_CALL

    agent_name: str = Field(..., description="Name of the agent making tool calls")
    tools: list[ToolCallInfo] = Field(..., description="List of tool calls requested")
    node_id: str = Field(..., description="Node ID associated with this tool call")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        # Agent name must not be empty
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()

class ToolExecutionResult(BaseModel):
    # Information about the result of ONE tool call.

    tool_call_id: str = Field(..., description="ID of the tool call this result belongs to")
    tool_name: str = Field(..., description="Name of the executed tool")
    success: bool = Field(..., description="Whether the tool executed successfully")
    result: str | None = Field(default=None, description="Result or error message from tool execution")

class ToolExecution(BaseModel):
    # Message sent when the agent has executed all tool calls and received the results.

    type: Literal[MessageType.TOOL_EXECUTION] = MessageType.TOOL_EXECUTION
    agent_name: str = Field(..., description="Name of the agent that executed tools")
    results: list[ToolExecutionResult] = Field(..., description="List of execution results")
    node_id: str = Field(..., description="Node ID associated with this execution")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        # Agent name must not be empty
        if not v or not v.strip():
            raise ValueError("agent_name cannot be empty")
        return v.strip()


from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field


class StateSnapshot(BaseModel):
    """Snapshot of all three states at a specific message index."""

    message_index: int = Field(description="Position in message thread (0-based)")
    state_of_run_text: str = Field(description="Current research progress state as text")
    tool_call_facts_text: str = Field(description="Discovered facts whiteboard as text")
    handoff_context_text: str = Field(description="Agent selection rules as text")


class BaseState(BaseModel):
    """Base class for all saveable state"""

    type: str = Field(default="BaseState")
    version: str = Field(default="1.0.0")


class AssistantAgentState(BaseState):
    """State for an assistant agent."""

    llm_context: Mapping[str, Any] = Field(default_factory=lambda: dict([("messages", [])]))
    type: str = Field(default="AssistantAgentState")


class TeamState(BaseState):
    """State for a team of agents."""

    agent_states: Mapping[str, Any] = Field(default_factory=dict)
    type: str = Field(default="TeamState")


class BaseGroupChatManagerState(BaseState):
    """Base state for all group chat managers."""

    message_thread: List[Mapping[str, Any]] = Field(default_factory=list)
    current_turn: int = Field(default=0)
    type: str = Field(default="BaseGroupChatManagerState")


class ChatAgentContainerState(BaseState):
    """State for a container of chat agents."""

    agent_state: Mapping[str, Any] = Field(default_factory=dict)
    message_buffer: List[Mapping[str, Any]] = Field(default_factory=list)
    type: str = Field(default="ChatAgentContainerState")


class RoundRobinManagerState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.RoundRobinGroupChat` manager."""

    next_speaker_index: int = Field(default=0)
    type: str = Field(default="RoundRobinManagerState")


class SelectorManagerState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.SelectorGroupChat` manager."""

    previous_speaker: Optional[str] = Field(default=None)
    # NEW: State text fields for three-state context management
    state_of_run_text: str = Field(default="", description="Current research state as text")
    tool_call_facts_text: str = Field(default="", description="Discovered facts whiteboard as text")
    handoff_context_text: str = Field(default="", description="Handoff selection rules as text")
    # NEW: Snapshots dictionary (uses string keys for JSON compatibility)
    state_snapshots: Dict[str, Mapping[str, Any]] = Field(
        default_factory=dict,
        description="Message index -> StateSnapshot (keys are strings for JSON compatibility)"
    )
    type: str = Field(default="SelectorManagerState")


class SwarmManagerState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.Swarm` manager."""

    current_speaker: str = Field(default="")
    type: str = Field(default="SwarmManagerState")


class MagenticOneOrchestratorState(BaseGroupChatManagerState):
    """State for :class:`~autogen_agentchat.teams.MagneticOneGroupChat` orchestrator."""

    task: str = Field(default="")
    facts: str = Field(default="")
    plan: str = Field(default="")
    n_rounds: int = Field(default=0)
    n_stalls: int = Field(default=0)
    type: str = Field(default="MagenticOneOrchestratorState")


class SocietyOfMindAgentState(BaseState):
    """State for a Society of Mind agent."""

    inner_team_state: Mapping[str, Any] = Field(default_factory=dict)
    type: str = Field(default="SocietyOfMindAgentState")

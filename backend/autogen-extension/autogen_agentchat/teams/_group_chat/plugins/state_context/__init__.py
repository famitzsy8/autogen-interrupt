"""State Context Plugin for cognitive offloading via three-state model.

This plugin provides external memory for the research process:
- StateOfRun: Current progress and next steps
- ToolCallFacts: Verified facts from tool executions
- HandoffContext: Agent selection rules and user preferences
"""
from ._models import StateSnapshot, StateUpdateEvent
from ._prompts import (
    STATE_OF_RUN_UPDATE_PROMPT,
    TOOL_CALL_UPDATING_PROMPT,
    HANDOFF_CONTEXT_UPDATING_PROMPT,
)
from ._handoff_intent_router import HandoffIntentRouter
from ._plugin import StateContextPlugin

__all__ = [
    "StateSnapshot",
    "StateUpdateEvent",
    "STATE_OF_RUN_UPDATE_PROMPT",
    "TOOL_CALL_UPDATING_PROMPT",
    "HANDOFF_CONTEXT_UPDATING_PROMPT",
    "HandoffIntentRouter",
    "StateContextPlugin",
]

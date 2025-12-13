"""State Context Plugin implementation for cognitive offloading."""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Sequence

from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient, CreateResult, SystemMessage, UserMessage

from .....messages import BaseAgentEvent, BaseChatMessage, ToolCallExecutionEvent
from ..._events import StateUpdateEvent
from ._handoff_intent_router import HandoffIntentRouter
from ._models import StateSnapshot
from ._prompts import (
    HANDOFF_CONTEXT_UPDATING_PROMPT,
    STATE_OF_RUN_UPDATE_PROMPT,
    TOOL_CALL_UPDATING_PROMPT,
)

logger = logging.getLogger(__name__)


class StateContextPlugin:
    """Plugin that manages three-state context for cognitive offloading.

    Maintains:
    - state_of_run: Current research progress and next steps
    - tool_call_facts: Verified facts from tool executions
    - handoff_context: Agent selection rules and user preferences
    """

    def __init__(
        self,
        model_client: ChatCompletionClient,
        initial_state_of_run: str = "",
        initial_handoff_context: str = "",
        user_proxy_name: str = "user_proxy",
        participant_names: list[str] | None = None,
    ) -> None:
        self._model_client = model_client
        self._user_proxy_name = user_proxy_name
        self._participant_names = participant_names or []

        # State text fields
        self._state_of_run_text = initial_state_of_run
        self._tool_call_facts_text = ""
        self._handoff_context_text = initial_handoff_context

        # Snapshots for branching
        self._state_snapshots: dict[int, StateSnapshot] = {}

        # Intent router for detecting handoff logic changes
        self._intent_router = HandoffIntentRouter(model_client)

        # Track message index
        self._current_thread_length = 0

        # Interrupted flag (set by manager)
        self._interrupted = False

        # Event emitter callback (set by manager)
        self._emit_event: Callable[[Any], Awaitable[None]] | None = None

    @property
    def name(self) -> str:
        return "state_context"

    async def on_message_added(
        self,
        message: BaseAgentEvent | BaseChatMessage,
        thread: Sequence[BaseAgentEvent | BaseChatMessage],
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Update state based on new message.

        Tool results update ToolCallFacts, agent messages update StateOfRun.
        Creates snapshots after state updates.
        """
        if self._interrupted:
            return

        self._current_thread_length = len(thread)

        # Update tool_call_facts if this is a tool execution
        if isinstance(message, ToolCallExecutionEvent):
            try:
                await self._update_tool_call_facts(message, cancellation_token)
                await self._create_snapshot()
            except Exception as e:
                logger.warning(f"Failed to update ToolCallFacts: {e}")

        # Update state_of_run for agent chat messages
        elif isinstance(message, BaseChatMessage):
            # Skip state updates for system/special messages
            source = message.source
            if source.lower() not in ('system', 'selector'):
                try:
                    await self._update_state_of_run(message, cancellation_token)
                    await self._create_snapshot()
                except Exception as e:
                    logger.warning(f"Failed to update StateOfRun: {e}")

    async def on_before_speaker_selection(
        self,
        thread: Sequence[BaseAgentEvent | BaseChatMessage],
        candidates: list[str],
        participant_names: list[str],
    ) -> str | None:
        """No speaker override - returns None."""
        return None

    async def on_user_message(
        self,
        message: BaseChatMessage,
        is_directed: bool,
        target: str | None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """User messages always update StateOfRun and HandoffContext.

        Detects explicit handoff intent and updates context accordingly.
        """
        if self._interrupted:
            return

        # Determine if this is a human message (from user proxy or external user)
        is_human_message = (
            message.source == self._user_proxy_name or
            message.source not in self._participant_names
        )

        if is_human_message:
            # REMOVED for efficiency's sake: See Context Engineering section in thesis
            
            # Human messages ALWAYS update both StateOfRun and HandoffContext
            # try:
            #     await self._update_state_of_run(message, cancellation_token)
            # except Exception as e:
            #     logger.exception(f"Exception in _update_state_of_run: {type(e).__name__}: {e}")
            # try:
            #     await self._update_handoff_context(message, cancellation_token)
            # except Exception as e:
            #     logger.exception(f"Exception in _update_handoff_context: {type(e).__name__}: {e}")

            # Additionally check for explicit handoff intent
            # try:
            #     has_intent = await self._intent_router.detect_intent(message.to_text())
            #     if has_intent:
            #         logger.debug("Explicit handoff intent detected in human message")
            # except Exception as e:
            #     logger.exception(f"Exception in intent detection: {type(e).__name__}: {e}")

            # # Create snapshot after state updates
            # try:
            #     await self._create_snapshot()
            # except Exception as e:
            #     logger.exception(f"Exception in _create_snapshot: {type(e).__name__}: {e}")
            pass

    async def on_branch(self, trim_count: int, new_thread_length: int) -> None:
        """Recover state from snapshot at or before new thread end.

        When conversation branches (messages are trimmed), restore state
        to the most recent snapshot at or before the trim point.

        Snapshots are sparse (not every message creates one), so we find
        the nearest snapshot at or before the new end of the thread.
        """
        last_idx = new_thread_length - 1

        # Find the nearest snapshot at or before last_idx
        # (snapshots are sparse - not every message index has one)
        nearest_snapshot_idx = None
        if last_idx >= 0 and self._state_snapshots:
            valid_indices = [k for k in self._state_snapshots.keys() if k <= last_idx]
            if valid_indices:
                nearest_snapshot_idx = max(valid_indices)

        if nearest_snapshot_idx is not None:
            snap = self._state_snapshots[nearest_snapshot_idx]
            self._state_of_run_text = snap.state_of_run_text
            self._tool_call_facts_text = snap.tool_call_facts_text
            self._handoff_context_text = snap.handoff_context_text
            logger.debug(f"Recovered state from snapshot at index {nearest_snapshot_idx} (trim point was {last_idx})")
        else:
            # No snapshot found - reset to initial state
            logger.warning(f"No snapshot found at or before index {last_idx}, resetting to empty state")
            self._state_of_run_text = ""
            self._tool_call_facts_text = ""
            self._handoff_context_text = ""

        # Clean up snapshots beyond trim point
        self._state_snapshots = {k: v for k, v in self._state_snapshots.items() if k < new_thread_length}
        self._current_thread_length = new_thread_length

    def get_state_for_agent(self) -> dict[str, Any]:
        """State injected into agent system prompts.

        Returns dictionary with state variables that agents can use
        for context in their prompt templates.
        """
        return {
            "state_of_run": self._state_of_run_text,
            "tool_call_facts": self._tool_call_facts_text,
            "handoff_context": self._handoff_context_text,
            "participant_names": self._participant_names,
        }

    def get_state_for_selector(self) -> dict[str, Any]:
        """State available in selector prompt template.

        Returns dictionary with state variables for speaker selection.
        """
        return {
            "state_of_run": self._state_of_run_text,
            "handoff_context": self._handoff_context_text,
        }

    async def save_state(self) -> dict[str, Any]:
        """Persist plugin state for session save/load."""
        return {
            "state_of_run": self._state_of_run_text,
            "tool_call_facts": self._tool_call_facts_text,
            "handoff_context": self._handoff_context_text,
            "snapshots": {str(k): v.model_dump() for k, v in self._state_snapshots.items()},
            "current_thread_length": self._current_thread_length,
        }

    async def load_state(self, state: dict[str, Any]) -> None:
        """Restore plugin state from saved session."""
        self._state_of_run_text = state.get("state_of_run", "")
        self._tool_call_facts_text = state.get("tool_call_facts", "")
        self._handoff_context_text = state.get("handoff_context", "")
        self._current_thread_length = state.get("current_thread_length", 0)

        if "snapshots" in state:
            self._state_snapshots = {
                int(k): StateSnapshot.model_validate(v)
                for k, v in state["snapshots"].items()
            }
        else:
            self._state_snapshots = {}

    # --- Private methods (state update logic) ---

    async def _create_snapshot(self) -> None:
        """Create a snapshot of current state at current message index.

        IMPORTANT: User messages ALWAYS create snapshots (they always update StateOfRun).
        Snapshots are sparse - not every message creates a snapshot (tool requests don't change state).
        """
        try:
            # Calculate message index (0-based)
            msg_idx = self._current_thread_length - 1

            if msg_idx < 0:
                logger.warning("Cannot create snapshot: message thread is empty")
                return

            # Create StateSnapshot with all three current state texts and participant names
            snapshot = StateSnapshot(
                message_index=msg_idx,
                state_of_run_text=self._state_of_run_text,
                tool_call_facts_text=self._tool_call_facts_text,
                handoff_context_text=self._handoff_context_text,
                participant_names=self._participant_names
            )

            # Store in snapshots dict
            self._state_snapshots[msg_idx] = snapshot

            # Emit state update event to output stream
            if self._emit_event:
                state_event = StateUpdateEvent(
                    source="state_context",
                    state_of_run=self._state_of_run_text,
                    tool_call_facts=self._tool_call_facts_text,
                    handoff_context=self._handoff_context_text,
                    message_index=msg_idx
                )
                await self._emit_event(state_event)

        except Exception as e:
            logger.exception(f"Exception in _create_snapshot: {type(e).__name__}: {e}")

    async def _update_state_of_run(
        self,
        agent_message: BaseChatMessage,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Update StateOfRun from agent message using LLM.

        Args:
            agent_message: Message from agent describing what it did
            cancellation_token: Token to cancel the LLM call if interrupt occurs
        """
        if self._interrupted:
            return

        try:
            # Extract message content as text
            message_text = agent_message.to_text()

            # Determine if this is from user proxy (for special handling)
            from_user_proxy = agent_message.source == self._user_proxy_name
            handoff_info = "just received user feedback" if from_user_proxy else self._handoff_context_text

            # Format prompt with current state and agent message
            prompt = STATE_OF_RUN_UPDATE_PROMPT.format(
                stateOfRun=self._state_of_run_text,
                handoffContext=handoff_info,
                agentMessage=message_text
            )

            # Wrap LLM call in task to make it cancellable
            async def _make_llm_call() -> CreateResult:
                result = await self._model_client.create(
                    messages=[
                        SystemMessage(content="You are updating research progress state."),
                        UserMessage(content=prompt, source="manager")
                    ]
                )
                return result

            task = asyncio.create_task(_make_llm_call())
            if cancellation_token:
                cancellation_token.link_future(task)

            response = await task

            # Store response directly as new state
            self._state_of_run_text = response.content if isinstance(response.content, str) else str(response.content)

        except Exception as e:
            logger.exception(f"Exception in _update_state_of_run: {type(e).__name__}: {e}")

    async def _update_tool_call_facts(
        self,
        tool_result_message: ToolCallExecutionEvent,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Update ToolCallFacts from tool execution results using LLM.

        IMPORTANT: Only RAW tool execution results should be passed to this method.
        The prompt will handle summarization.

        Args:
            tool_result_message: Message containing ONLY raw tool execution results
            cancellation_token: Token to cancel the LLM call if interrupt occurs
        """
        if self._interrupted:
            return

        try:
            # Extract message content as text
            message_text = tool_result_message.to_text()

            # Format prompt with current facts and tool results
            prompt = TOOL_CALL_UPDATING_PROMPT.format(
                toolCallFacts=self._tool_call_facts_text,
                toolCallExecutionResults=message_text
            )

            # Wrap LLM call in task to make it cancellable
            async def _make_llm_call() -> CreateResult:
                result = await self._model_client.create(
                    messages=[
                        SystemMessage(content="You are updating the discovered facts whiteboard."),
                        UserMessage(content=prompt, source="manager")
                    ]
                )
                return result

            task = asyncio.create_task(_make_llm_call())
            if cancellation_token:
                cancellation_token.link_future(task)

            response = await task

            # Concatenate new additions to existing whiteboard
            new_additions = response.content if isinstance(response.content, str) else str(response.content)
            self._tool_call_facts_text = self._tool_call_facts_text + "\n\n" + new_additions

        except Exception as e:
            logger.warning(f"Failed to update ToolCallFacts: {e}")

    async def _update_handoff_context(
        self,
        user_message: BaseChatMessage,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Update HandoffContext from user message using LLM.

        Args:
            user_message: Message from user providing new handoff instructions
            cancellation_token: Token to cancel the LLM call if interrupt occurs
        """
        if self._interrupted:
            return

        try:
            # Extract message content as text
            message_text = user_message.to_text()

            # Format prompt with current state, context, and message
            prompt = HANDOFF_CONTEXT_UPDATING_PROMPT.format(
                stateOfRun=self._state_of_run_text,
                handoffContext=self._handoff_context_text,
                user_message=message_text
            )

            # Wrap LLM call in task to make it cancellable
            async def _make_llm_call() -> CreateResult:
                result = await self._model_client.create(
                    messages=[
                        SystemMessage(content="You are updating handoff instructions."),
                        UserMessage(content=prompt, source="manager")
                    ]
                )
                return result

            task = asyncio.create_task(_make_llm_call())
            if cancellation_token:
                cancellation_token.link_future(task)

            response = await task

            # Store response directly as new handoff context
            self._handoff_context_text = response.content if isinstance(response.content, str) else str(response.content)
            logger.debug(f"HandoffContext updated ({len(self._handoff_context_text)} chars)")

        except Exception as e:
            logger.warning(f"Failed to update HandoffContext: {e}")

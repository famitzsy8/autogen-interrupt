import asyncio
import logging
import re
import tiktoken
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Union, cast

from autogen_core import AgentRuntime, CancellationToken, Component, ComponentModel, DefaultTopicId, MessageContext, event, rpc
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelFamily,
    SystemMessage,
    UserMessage,
)
from autogen_agentchat.teams._group_chat._state_prompts import (
    STATE_OF_RUN_UPDATE_PROMPT,
    TOOL_CALL_UPDATING_PROMPT,
    HANDOFF_CONTEXT_UPDATING_PROMPT
)
from autogen_agentchat.teams._group_chat._handoff_intent_router import HandoffIntentRouter
from pydantic import BaseModel
from typing_extensions import Self

from ... import TRACE_LOGGER_NAME
from ...base import ChatAgent, Team, TerminationCondition
from ...messages import (
    BaseAgentEvent,
    BaseChatMessage,
    HandoffMessage,
    MessageFactory,
    ModelClientStreamingChunkEvent,
    SelectorEvent,
    ToolCallExecutionEvent,
)
from ...state import SelectorManagerState, StateSnapshot
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager
from ._events import (
    GroupChatAgentResponse,
    GroupChatBranch,
    GroupChatRequestPublish,
    GroupChatStart,
    GroupChatTeamResponse,
    GroupChatTermination,
    UserDirectedMessage,
)
from ._node_message_mapping import count_messages_for_node_trim
from ._agent_buffer_node_mapping import convert_manager_trim_to_agent_trim

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
message_thread_logger = logging.getLogger(f"{__name__}.message_thread")
logger = logging.getLogger(__name__)

# Initialize tiktoken encoder for token counting
def _get_tiktoken_encoder() -> tiktoken.Encoding:
    """Get the tiktoken encoder for GPT-3.5/4 models."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback to a simple token counter if tiktoken fails
        return None

_tiktoken_encoder = _get_tiktoken_encoder()

def _count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    if _tiktoken_encoder is None:
        # Fallback: rough estimate of 4 chars per token
        return len(text) // 4
    try:
        return len(_tiktoken_encoder.encode(text))
    except Exception:
        return len(text) // 4

# Configure logging at module import time
def _setup_selector_logging() -> None:
    """Setup logging configuration for selector group chat."""
    import sys

    if not message_thread_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        message_thread_logger.addHandler(handler)
        message_thread_logger.setLevel(logging.INFO)
        message_thread_logger.propagate = False

        print("✅ SELECTOR GROUP CHAT LOGGER INITIALIZED", flush=True)

_setup_selector_logging()


SyncSelectorFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], str | None]
AsyncSelectorFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[str | None]]
SelectorFuncType = Union[SyncSelectorFunc | AsyncSelectorFunc]

SyncCandidateFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], List[str]]
AsyncCandidateFunc = Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[List[str]]]
CandidateFuncType = Union[SyncCandidateFunc | AsyncCandidateFunc]


class SelectorGroupChatManager(BaseGroupChatManager):
    """A group chat manager that selects the next speaker using a ChatCompletion
    model and a custom selector function."""

    def __init__(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        model_client: ChatCompletionClient,
        selector_prompt: str,
        allow_repeated_speaker: bool,
        selector_func: Optional[SelectorFuncType],
        max_selector_attempts: int,
        candidate_func: Optional[CandidateFuncType],
        emit_team_events: bool,
        model_context: ChatCompletionContext | None,
        model_client_streaming: bool = False,
        agent_input_queue: Any | None = None,
        enable_state_context: bool = True,
        user_proxy_name: str = "user_proxy",
        initial_handoff_context: str | None = None,
        initial_state_of_run: str | None = None,
        state_model_client: ChatCompletionClient | None = None,
    ) -> None:
        super().__init__(
            name,
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_names,
            participant_descriptions,
            output_message_queue,
            termination_condition,
            max_turns,
            message_factory,
            emit_team_events,
            agent_input_queue=agent_input_queue,
        )
        self._model_client = model_client
        # Use separate model client for state updates if provided, otherwise use main client
        self._state_model_client = state_model_client or model_client
        self._selector_prompt = selector_prompt
        self._previous_speaker: str | None = None
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func
        self._is_selector_func_async = iscoroutinefunction(self._selector_func)
        self._max_selector_attempts = max_selector_attempts
        self._candidate_func = candidate_func
        self._is_candidate_func_async = iscoroutinefunction(self._candidate_func)
        self._model_client_streaming = model_client_streaming
        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()
        self._cancellation_token = CancellationToken()

        # State context management
        self._enable_state_context = enable_state_context
        self._user_proxy_name = user_proxy_name

        # Initialize states as empty strings (or initial context if provided)
        self._state_of_run_text: str = initial_state_of_run or ""
        self._tool_call_facts_text: str = ""
        self._handoff_context_text: str = initial_handoff_context or ""

        # Initialize snapshots dict (sparse - only entries for state changes)
        self._state_snapshots: Dict[int, Any] = {}

        # Initialize intent router for detecting handoff intent in user messages
        self._intent_router = HandoffIntentRouter(model_client)

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def reset(self) -> None:
        reset_msg = f"\n{'='*80}\n🔄 RESETTING MESSAGE THREAD (previous size: {len(self._message_thread)})\n{'='*80}\n"
        message_thread_logger.info(reset_msg)
        print(reset_msg, flush=True)

        self._current_turn = 0
        self._message_thread.clear()
        await self._model_context.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._previous_speaker = None

        success_msg = "✅ Message thread reset successfully\n"
        message_thread_logger.info(success_msg)
        print(success_msg, flush=True)

    async def save_state(self) -> Mapping[str, Any]:
        """Save manager state including three-state context."""
        # NEW: Save snapshots (convert int keys to str for JSON compatibility)
        snapshots_dict = {}
        for idx, snap in self._state_snapshots.items():
            snapshots_dict[str(idx)] = snap.model_dump()

        state = SelectorManagerState(
            message_thread=[msg.dump() for msg in self._message_thread],
            current_turn=self._current_turn,
            previous_speaker=self._previous_speaker,
            # NEW: Save state strings
            state_of_run_text=self._state_of_run_text,
            tool_call_facts_text=self._tool_call_facts_text,
            handoff_context_text=self._handoff_context_text,
            # NEW: Save snapshots (already converted above)
            state_snapshots=snapshots_dict,
        )

        result = state.model_dump()
        return result

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load manager state including three-state context."""
        selector_state = SelectorManagerState.model_validate(state)

        # Existing restoration logic
        self._message_thread = [self._message_factory.create(msg) for msg in selector_state.message_thread]
        await self._add_messages_to_context(
            self._model_context, [msg for msg in self._message_thread if isinstance(msg, BaseChatMessage)]
        )
        self._current_turn = selector_state.current_turn
        self._previous_speaker = selector_state.previous_speaker

        # NEW: Restore state strings (use .get() with default for backward compatibility)
        self._state_of_run_text = selector_state.state_of_run_text or ""
        self._tool_call_facts_text = selector_state.tool_call_facts_text or ""
        self._handoff_context_text = selector_state.handoff_context_text or ""

        # NEW: Restore snapshots (convert str keys back to int)
        if selector_state.state_snapshots:
            self._state_snapshots = {
                int(idx): StateSnapshot.model_validate(snap)
                for idx, snap in selector_state.state_snapshots.items()
            }
        else:
            self._state_snapshots = {}

    async def _create_state_snapshot(self) -> None:
        """Create a snapshot of current state at current message index.

        IMPORTANT: User messages ALWAYS create snapshots (they always update StateOfRun).
        Snapshots are sparse - not every message creates a snapshot (tool requests don't change state).
        """
        if not self._enable_state_context:
            return

        try:
            # Calculate message index (0-based)
            msg_idx = len(self._message_thread) - 1

            if msg_idx < 0:
                logger.warning("Cannot create snapshot: message thread is empty")
                return

            # Create StateSnapshot with all three current state texts
            snapshot = StateSnapshot(
                message_index=msg_idx,
                state_of_run_text=self._state_of_run_text,
                tool_call_facts_text=self._tool_call_facts_text,
                handoff_context_text=self._handoff_context_text
            )

            # Store in snapshots dict
            self._state_snapshots[msg_idx] = snapshot
            logger.debug(f"✓ Snapshot created at index {msg_idx}")
        except Exception as e:
            logger.exception(f"Exception in _create_state_snapshot: {type(e).__name__}: {e}")

    async def _update_state_of_run(self, agent_message: BaseChatMessage, cancellation_token: CancellationToken | None = None) -> None:
        """Update StateOfRun from agent message using LLM.

        Args:
            agent_message: Message from agent describing what it did
            cancellation_token: Token to cancel the LLM call if interrupt occurs
        """
        if not self._enable_state_context:
            return

        if self._interrupted:
            return

        try:
            # Extract message content as text
            message_text = agent_message.to_text()

            # Format prompt with current state and agent message
            prompt = STATE_OF_RUN_UPDATE_PROMPT.format(
                stateOfRun=self._state_of_run_text,
                agentMessage=message_text
            )

            # Wrap LLM call in task to make it cancellable (matching agent tool call pattern)
            async def _make_llm_call() -> Any:
                return await self._state_model_client.create(
                    messages=[
                        SystemMessage(content="You are updating research progress state."),
                        UserMessage(content=prompt, source="manager")
                    ]
                )

            task = asyncio.create_task(_make_llm_call())
            if cancellation_token:
                cancellation_token.link_future(task)

            response = await task

            # Store response directly as new state
            self._state_of_run_text = response.content if isinstance(response.content, str) else str(response.content)
            logger.debug(f"✓ StateOfRun updated ({len(self._state_of_run_text)} chars)")

        except Exception as e:
            logger.exception(f"Exception in _update_state_of_run: {type(e).__name__}: {e}")

    async def _update_tool_call_facts(self, tool_result_message: BaseAgentEvent, cancellation_token: CancellationToken | None = None) -> None:
        """Update ToolCallFacts from tool execution results using LLM.

        IMPORTANT: Only RAW tool execution results should be passed to this method.
        The prompt will handle summarization. Agent analysis/commentary should NOT
        appear in tool_result_message.

        Args:
            tool_result_message: Message containing ONLY raw tool execution results
            cancellation_token: Token to cancel the LLM call if interrupt occurs
        """
        if not self._enable_state_context:
            return

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

            # Wrap LLM call in task to make it cancellable (matching agent tool call pattern)
            async def _make_llm_call() -> Any:
                return await self._state_model_client.create(
                    messages=[
                        SystemMessage(content="You are updating the discovered facts whiteboard."),
                        UserMessage(content=prompt, source="manager")
                    ]
                )

            task = asyncio.create_task(_make_llm_call())
            if cancellation_token:
                cancellation_token.link_future(task)

            response = await task

            # Store response directly as new facts
            self._tool_call_facts_text = response.content if isinstance(response.content, str) else str(response.content)
            logger.debug(f"✓ ToolCallFacts updated ({len(self._tool_call_facts_text)} chars)")

        except Exception as e:
            logger.warning(f"Failed to update ToolCallFacts: {e}")

    async def _update_handoff_context(self, user_message: BaseChatMessage, cancellation_token: CancellationToken | None = None) -> None:
        """Update HandoffContext from user message using LLM.

        Args:
            user_message: Message from user providing new handoff instructions
            cancellation_token: Token to cancel the LLM call if interrupt occurs
        """
        if not self._enable_state_context:
            return

        if self._interrupted:
            return

        try:
            # Extract message content as text
            message_text = user_message.to_text()

            # Format prompt with current state, context, user proxy name, and message
            prompt = HANDOFF_CONTEXT_UPDATING_PROMPT.format(
                stateOfRun=self._state_of_run_text,
                handoffContext=self._handoff_context_text,
                user_proxy_name=self._user_proxy_name,
                user_message=message_text
            )

            # Wrap LLM call in task to make it cancellable (matching agent tool call pattern)
            async def _make_llm_call() -> Any:
                return await self._state_model_client.create(
                    messages=[
                        SystemMessage(content="You are updating handoff instructions."),
                        UserMessage(content=prompt, source="manager")
                    ]
                )

            task = asyncio.create_task(_make_llm_call())
            if cancellation_token:
                cancellation_token.link_future(task)

            response = await task

            # Store response directly as new handoff context
            self._handoff_context_text = response.content if isinstance(response.content, str) else str(response.content)
            logger.debug(f"✓ HandoffContext updated ({len(self._handoff_context_text)} chars)")

        except Exception as e:
            logger.warning(f"Failed to update HandoffContext: {e}")

    # def _log_complete_state(self, event: str = "State Update") -> None:
    #     """FOR TESTING -- TO REMOVE: Log complete current state.
    #
    #     Args:
    #         event: Description of the event that triggered this state dump
    #     """
    #     message_thread_logger.info(f"\n{'#'*80}")
    #     message_thread_logger.info(f"# COMPLETE STATE SNAPSHOT: {event}")
    #     message_thread_logger.info(f"{'#'*80}")
    #     message_thread_logger.info(f"# State of Run:")
    #     message_thread_logger.info(f"{self._state_of_run_text}")
    #     message_thread_logger.info(f"\n# Tool Call Facts:")
    #     message_thread_logger.info(f"{self._tool_call_facts_text if self._tool_call_facts_text else '(empty)'}")
    #     message_thread_logger.info(f"\n# Handoff Context:")
    #     message_thread_logger.info(f"{self._handoff_context_text if self._handoff_context_text else '(empty)'}")
    #     message_thread_logger.info(f"{'#'*80}\n")

    def get_current_state_package(self) -> dict[str, str]:
        """Get current state package for passing to agents.

        Returns:
            Dict with keys: 'state_of_run', 'tool_call_facts', 'handoff_context'
            Each value is the current state text string.

        This is called by ChatAgentContainer via callback to inject state into agent buffers.
        """
        # FOR TESTING -- TO REMOVE: Log when state is requested
        message_thread_logger.info(f"# FOR TESTING -- TO REMOVE: State package requested by container")
        return {
            'state_of_run': self._state_of_run_text,
            'tool_call_facts': self._tool_call_facts_text,
            'handoff_context': self._handoff_context_text,
        }

    @rpc
    async def handle_user_directed_message(self, message: UserDirectedMessage, ctx: MessageContext) -> None:  # type: ignore[override]
        """Handle a user-directed message with trim logic and state recovery.

        Overrides base class to add state snapshot recovery when trimming the message thread.
        """
        self._interrupted = False
        target = message.target
        trim_up = message.trim_up
        self._old_threads.append(self._message_thread)

        # Handle trim operations with state recovery
        if trim_up > 0:
            logger.info(f"Trimming conversation: removing last {trim_up} nodes")
            logger.debug(f"Before trim - Thread length: {len(self._message_thread)}")

            # Calculate trim amounts for manager and agents
            messages_to_trim = count_messages_for_node_trim(self._message_thread, trim_up)
            agent_trim_up = convert_manager_trim_to_agent_trim(self._message_thread, trim_up)

            logger.debug(f"Calculated messages_to_trim: {messages_to_trim}")

            # Slice message thread to new length
            self._message_thread = self._message_thread[:-messages_to_trim]

            logger.debug(f"After trim - Thread length: {len(self._message_thread)}")

            # Recover states from snapshot at trim point
            if self._enable_state_context and len(self._message_thread) > 0:
                last_message_idx = len(self._message_thread) - 1

                if last_message_idx in self._state_snapshots:
                    snap = self._state_snapshots[last_message_idx]
                    self._state_of_run_text = snap.state_of_run_text
                    self._tool_call_facts_text = snap.tool_call_facts_text
                    self._handoff_context_text = snap.handoff_context_text
                    logger.info(f"✓ States recovered from snapshot at index {last_message_idx}")
                else:
                    logger.debug(f"No snapshot at index {last_message_idx}, states unchanged")

                # Clean old snapshots beyond trim point
                old_snapshot_count = len(self._state_snapshots)
                self._state_snapshots = {
                    k: v for k, v in self._state_snapshots.items()
                    if k < len(self._message_thread)
                }
                removed_count = old_snapshot_count - len(self._state_snapshots)
                logger.debug(f"Cleaned {removed_count} snapshots beyond trim point")

            # Broadcast branch event to all agents
            await self.publish_message(
                GroupChatBranch(agent_trim_up=agent_trim_up),
                topic_id=DefaultTopicId(type=self._group_topic_type),
                cancellation_token=ctx.cancellation_token,
            )

        if target not in self._participant_name_to_topic_type:
            raise ValueError(f"Target {target} not found in participant names {self._participant_names}")

        # Send user message to output and agents
        await self.publish_message(
            GroupChatStart(messages=[message.message]),
            topic_id=DefaultTopicId(type=self._output_topic_type),
        )
        await self._output_message_queue.put(message.message)

        await self.publish_message(
            GroupChatStart(messages=[message.message]),
            topic_id=DefaultTopicId(type=self._group_topic_type),
            cancellation_token=ctx.cancellation_token,
        )

        # Append to thread
        await self.update_message_thread([message.message])

        # NEW: Check if this message is from a human client (UserControlAgent or UserProxyAgent)
        # Messages in UserDirectedMessage come from the user control API, and the source
        # field tells us who sent it. Human messages are from:
        # - UserProxyAgent (source = _user_proxy_name, e.g., "user_proxy")
        # - UserControlAgent (source = "You" or custom name, not in _participant_names)
        logger.info(f"is_human: {self._enable_state_context}, {isinstance(message.message, BaseChatMessage)}, {message.message.source == self._user_proxy_name}, {message.message.source not in self._participant_names}, {message.message}, {message.message.source}")
        is_human_message = (
            self._enable_state_context and
            isinstance(message.message, BaseChatMessage) and
            (message.message.source == self._user_proxy_name or
             message.message.source not in self._participant_names)
        )

        if is_human_message:
            # Human messages ALWAYS update both StateOfRun and HandoffContext
            try:
                await self._update_state_of_run(message.message, ctx.cancellation_token)
            except Exception as e:
                logger.exception(f"Exception in _update_state_of_run: {type(e).__name__}: {e}")

            try:
                await self._update_handoff_context(message.message, ctx.cancellation_token)
            except Exception as e:
                logger.exception(f"Exception in _update_handoff_context: {type(e).__name__}: {e}")

            # Additionally check for explicit handoff intent
            try:
                has_intent = await self._intent_router.detect_intent(message.message.to_text())
                if has_intent:
                    logger.debug("Explicit handoff intent detected in human message")
            except Exception as e:
                logger.exception(f"Exception in intent detection: {type(e).__name__}: {e}")

            # Create snapshot after state updates
            try:
                await self._create_state_snapshot()
                logger.debug("✓ State snapshot created after human message")
            except Exception as e:
                logger.exception(f"Exception in _create_state_snapshot: {type(e).__name__}: {e}")

        # Check termination condition
        if await self._apply_termination_condition([message.message]):
            return

        # Send publish request to target speaker
        speaker_topic_type = self._participant_name_to_topic_type[target]
        await self.publish_message(
            GroupChatRequestPublish(),
            topic_id=DefaultTopicId(type=speaker_topic_type),
            cancellation_token=ctx.cancellation_token,
        )
        self._active_speakers.append(target)

    @event
    async def handle_agent_response(  # type: ignore[override]
        self, message: GroupChatAgentResponse | GroupChatTeamResponse, ctx: MessageContext
    ) -> None:
        """Handle agent response with state updates.

        Overrides base class to add state update triggers after agent messages.
        """
        if self._interrupted:
            self._active_speakers = []
            return

        try:
            # Log incoming response
            agent_name = message.name
            logger.debug(f"Received response from agent: {agent_name}")

            # Construct the delta from the agent response
            delta: List[BaseAgentEvent | BaseChatMessage] = []
            if isinstance(message, GroupChatAgentResponse):
                if message.response.inner_messages is not None:
                    for inner_message in message.response.inner_messages:
                        delta.append(inner_message)
                delta.append(message.response.chat_message)
            else:
                delta.extend(message.result.messages)

            # Append the messages to the message thread
            await self.update_message_thread(delta)

            # Check again for interrupt before doing state updates
            if self._interrupted:
                self._active_speakers.remove(message.name) if message.name in self._active_speakers else None
                return

            # NEW: Update states after messages are added to thread
            if self._enable_state_context:
                # Update ToolCallFacts from inner_messages (tool execution results)
                if isinstance(message, GroupChatAgentResponse):
                    if message.response.inner_messages is not None:
                        for inner_message in message.response.inner_messages:
                            # Tool result messages are BaseAgentEvent instances
                            if isinstance(inner_message, ToolCallExecutionEvent):
                                try:
                                    await self._update_tool_call_facts(inner_message, ctx.cancellation_token)
                                    await self._create_state_snapshot()
                                    logger.info("✓ ToolCallFacts updated and snapshot created")
                                except Exception as e:
                                    logger.warning(f"Failed to update ToolCallFacts: {e}")

                # Update StateOfRun from agent's chat message
                if isinstance(message, GroupChatAgentResponse):
                    try:
                        await self._update_state_of_run(message.response.chat_message, ctx.cancellation_token)
                        await self._create_state_snapshot()
                        logger.info("✓ StateOfRun updated and snapshot created")
                    except Exception as e:
                        logger.warning(f"Failed to update StateOfRun: {e}")
                else:
                    # For team responses, update from all messages
                    for msg in message.result.messages:
                        if isinstance(msg, BaseChatMessage):
                            try:
                                await self._update_state_of_run(msg, ctx.cancellation_token)
                                await self._create_state_snapshot()
                                logger.info("✓ StateOfRun updated and snapshot created")
                            except Exception as e:
                                logger.warning(f"Failed to update StateOfRun: {e}")

            # Remove the agent from the active speakers list
            self._active_speakers.remove(message.name)
            if len(self._active_speakers) > 0:
                # If there are still active speakers, return without doing anything
                return

            # Check if the conversation should be terminated
            if await self._apply_termination_condition(delta, increment_turn_count=True):
                # Stop the group chat
                return

            # Check for interrupt before expensive speaker selection
            if self._interrupted:
                return

            # Select speakers to continue the conversation
            await self._transition_to_next_speakers(ctx.cancellation_token)
        except Exception as e:
            # Handle the exception and signal termination with an error
            from ._events import SerializableException
            error = SerializableException.from_exception(e)
            await self._signal_termination_with_error(error)
            # Raise the exception to the runtime
            raise

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext,
        messages: Sequence[BaseChatMessage],
    ) -> None:
        """
        Add incoming messages to the model context.
        """
        for msg in messages:
            if isinstance(msg, HandoffMessage):
                for llm_msg in msg.context:
                    await model_context.add_message(llm_msg)
            await model_context.add_message(msg.to_model_message())

    async def update_message_thread(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        # Calculate token count for new messages
        new_tokens = 0
        for msg in messages:
            if hasattr(msg, 'content'):
                content = msg.content
                if isinstance(content, str):
                    new_tokens += _count_tokens(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, str):
                            new_tokens += _count_tokens(item)
                        else:
                            new_tokens += _count_tokens(str(item))
                else:
                    new_tokens += _count_tokens(str(content))

        # Extend the message thread
        self._message_thread.extend(messages)
        base_chat_messages = [m for m in messages if isinstance(m, BaseChatMessage)]
        await self._add_messages_to_context(self._model_context, base_chat_messages)

    async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str] | str:
        """Selects the next speaker in a group chat using a ChatCompletion client,
        with the selector function as override if it returns a speaker name.

        .. note::

            This method always returns a single speaker name.

        A key assumption is that the agent type is the same as the topic type, which we use as the agent name.
        """
        # Use the selector function if provided.
        if self._selector_func is not None:
            if self._is_selector_func_async:
                async_selector_func = cast(AsyncSelectorFunc, self._selector_func)
                speaker = await async_selector_func(thread)
            else:
                sync_selector_func = cast(SyncSelectorFunc, self._selector_func)
                speaker = sync_selector_func(thread)
            if speaker is not None:
                if speaker not in self._participant_names:
                    raise ValueError(
                        f"Selector function returned an invalid speaker name: {speaker}. "
                        f"Expected one of: {self._participant_names}."
                    )
                # Skip the model based selection.
                return [speaker]

        # Use the candidate function to filter participants if provided
        if self._candidate_func is not None:
            if self._is_candidate_func_async:
                async_candidate_func = cast(AsyncCandidateFunc, self._candidate_func)
                participants = await async_candidate_func(thread)
            else:
                sync_candidate_func = cast(SyncCandidateFunc, self._candidate_func)
                participants = sync_candidate_func(thread)
            if not participants:
                raise ValueError("Candidate function must return a non-empty list of participant names.")
            if not all(p in self._participant_names for p in participants):
                raise ValueError(
                    f"Candidate function returned invalid participant names: {participants}. "
                    f"Expected one of: {self._participant_names}."
                )
        else:
            # Construct the candidate agent list to be selected from, skip the previous speaker if not allowed.
            if self._previous_speaker is not None and not self._allow_repeated_speaker:
                participants = [p for p in self._participant_names if p != self._previous_speaker]
            else:
                participants = list(self._participant_names)

        assert len(participants) > 0

        # Construct agent roles.
        # Each agent sould appear on a single line.
        roles = ""
        for topic_type, description in zip(self._participant_names, self._participant_descriptions, strict=True):
            roles += re.sub(r"\s+", " ", f"{topic_type}: {description}").strip() + "\n"
        roles = roles.strip()

        # Select the next speaker.
        if len(participants) > 1:
            agent_name = await self._select_speaker(roles, participants, self._max_selector_attempts)
        else:
            agent_name = participants[0]
        self._previous_speaker = agent_name
        trace_logger.debug(f"Selected speaker: {agent_name}")
        return [agent_name]

    def construct_message_history(self, message_history: List[LLMMessage]) -> str:
        # Construct the history of the conversation.
        history_messages: List[str] = []
        for msg in message_history:
            if isinstance(msg, UserMessage) or isinstance(msg, AssistantMessage):
                message = f"{msg.source}: {msg.content}"
                history_messages.append(
                    message.rstrip() + "\n\n"
                )  # Create some consistency for how messages are separated in the transcript

        history: str = "\n".join(history_messages)
        return history

    async def _select_speaker(self, roles: str, participants: List[str], max_attempts: int) -> str:
        model_context_messages = await self._model_context.get_messages()
        model_context_history = self.construct_message_history(model_context_messages)

        select_speaker_prompt = self._selector_prompt.format(**{
            "roles": roles,
            "participants": str(participants),
            "history": model_context_history
        })
        

        select_speaker_messages: List[SystemMessage | UserMessage | AssistantMessage]
        if ModelFamily.is_openai(self._model_client.model_info["family"]):
            select_speaker_messages = [SystemMessage(content=select_speaker_prompt)]
        else:
            # Many other models need a UserMessage to respond to
            select_speaker_messages = [UserMessage(content=select_speaker_prompt, source="user")]

        num_attempts = 0
        while num_attempts < max_attempts:
            num_attempts += 1
            if self._model_client_streaming:
                chunk: CreateResult | str = ""
                async for _chunk in self._model_client.create_stream(messages=select_speaker_messages):
                    chunk = _chunk
                    if self._emit_team_events:
                        if isinstance(chunk, str):
                            await self._output_message_queue.put(
                                ModelClientStreamingChunkEvent(content=cast(str, _chunk), source=self._name)
                            )
                        else:
                            assert isinstance(chunk, CreateResult)
                            assert isinstance(chunk.content, str)
                            await self._output_message_queue.put(
                                SelectorEvent(content=chunk.content, source=self._name)
                            )
                # The last chunk must be CreateResult.
                assert isinstance(chunk, CreateResult)
                response = chunk
            else:
                response = await self._model_client.create(messages=select_speaker_messages)
            assert isinstance(response.content, str)
            select_speaker_messages.append(AssistantMessage(content=response.content, source="selector"))
            # NOTE: we use all participant names to check for mentions, even if the previous speaker is not allowed.
            # This is because the model may still select the previous speaker, and we want to catch that.
            mentions = self._mentioned_agents(response.content, self._participant_names)
            if len(mentions) == 0:
                trace_logger.debug(f"Model failed to select a valid name: {response.content} (attempt {num_attempts})")
                feedback = f"No valid name was mentioned. Please select from: {str(participants)}."
                select_speaker_messages.append(UserMessage(content=feedback, source="user"))
            elif len(mentions) > 1:
                trace_logger.debug(f"Model selected multiple names: {str(mentions)} (attempt {num_attempts})")
                feedback = (
                    f"Expected exactly one name to be mentioned. Please select only one from: {str(participants)}."
                )
                select_speaker_messages.append(UserMessage(content=feedback, source="user"))
            else:
                agent_name = list(mentions.keys())[0]
                if (
                    not self._allow_repeated_speaker
                    and self._previous_speaker is not None
                    and agent_name == self._previous_speaker
                ):
                    trace_logger.debug(f"Model selected the previous speaker: {agent_name} (attempt {num_attempts})")
                    feedback = (
                        f"Repeated speaker is not allowed, please select a different name from: {str(participants)}."
                    )
                    select_speaker_messages.append(UserMessage(content=feedback, source="user"))
                else:
                    # Valid selection
                    trace_logger.debug(f"Model selected a valid name: {agent_name} (attempt {num_attempts})")
                    return agent_name

        if self._previous_speaker is not None:
            trace_logger.warning(f"Model failed to select a speaker after {max_attempts}, using the previous speaker.")
            return self._previous_speaker
        trace_logger.warning(
            f"Model failed to select a speaker after {max_attempts} and there was no previous speaker, using the first participant."
        )
        return participants[0]

    def _mentioned_agents(self, message_content: str, agent_names: List[str]) -> Dict[str, int]:
        """Counts the number of times each agent is mentioned in the provided message content.
        Agent names will match under any of the following conditions (all case-sensitive):
        - Exact name match
        - If the agent name has underscores it will match with spaces instead (e.g. 'Story_writer' == 'Story writer')
        - If the agent name has underscores it will match with '\\_' instead of '_' (e.g. 'Story_writer' == 'Story\\_writer')

        Args:
            message_content (Union[str, List]): The content of the message, either as a single string or a list of strings.
            agents (List[Agent]): A list of Agent objects, each having a 'name' attribute to be searched in the message content.

        Returns:
            Dict: a counter for mentioned agents.
        """
        mentions: Dict[str, int] = dict()
        for name in agent_names:
            # Finds agent mentions, taking word boundaries into account,
            # accommodates escaping underscores and underscores as spaces
            regex = (
                r"(?<=\W)("
                + re.escape(name)
                + r"|"
                + re.escape(name.replace("_", " "))
                + r"|"
                + re.escape(name.replace("_", r"\_"))
                + r")(?=\W)"
            )
            # Pad the message to help with matching
            count = len(re.findall(regex, f" {message_content} "))
            if count > 0:
                mentions[name] = count
        return mentions


class SelectorGroupChatConfig(BaseModel):
    """The declarative configuration for SelectorGroupChat."""

    name: str | None = None
    description: str | None = None
    participants: List[ComponentModel]
    model_client: ComponentModel
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    selector_prompt: str
    allow_repeated_speaker: bool
    # selector_func: ComponentModel | None
    max_selector_attempts: int = 3
    emit_team_events: bool = False
    model_client_streaming: bool = False
    model_context: ComponentModel | None = None


class SelectorGroupChat(BaseGroupChat, Component[SelectorGroupChatConfig]):
    """A group chat team that have participants takes turn to publish a message
    to all, using a ChatCompletion model to select the next speaker after each message.

    If an :class:`~autogen_agentchat.base.ChatAgent` is a participant,
    the :class:`~autogen_agentchat.messages.BaseChatMessage` from the agent response's
    :attr:`~autogen_agentchat.base.Response.chat_message` will be published
    to other participants in the group chat.

    If a :class:`~autogen_agentchat.base.Team` is a participant,
    the :class:`~autogen_agentchat.messages.BaseChatMessage`
    from the team result' :attr:`~autogen_agentchat.base.TaskResult.messages` will be published
    to other participants in the group chat.

    Args:
        participants (List[ChatAgent | Team]): The participants in the group chat,
            must have unique names and at least two participants.
        model_client (ChatCompletionClient): The ChatCompletion model client used
            to select the next speaker.
        name (str | None, optional): The name of the group chat, using
            :attr:`~autogen_agentchat.teams.SelectorGroupChat.DEFAULT_NAME` if not provided.
            The name is used by a parent team to identify this group chat so it must
            be unique within the parent team.
        description (str | None, optional): The description of the group chat, using
            :attr:`~autogen_agentchat.teams.SelectorGroupChat.DEFAULT_DESCRIPTION` if not provided.
        termination_condition (TerminationCondition, optional): The termination condition for the group chat. Defaults to None.
            Without a termination condition, the group chat will run indefinitely.
        max_turns (int, optional): The maximum number of turns in the group chat before stopping. Defaults to None, meaning no limit.
        selector_prompt (str, optional): The prompt template to use for selecting the next speaker.
            Available fields: '{roles}', '{participants}', and '{history}'.
            `{participants}` is the names of candidates for selection. The format is `["<name1>", "<name2>", ...]`.
            `{roles}` is a newline-separated list of names and descriptions of the candidate agents. The format for each line is: `"<name> : <description>"`.
            `{history}` is the conversation history formatted as a double newline separated of names and message content. The format for each message is: `"<name> : <message content>"`.
        allow_repeated_speaker (bool, optional): Whether to include the previous speaker in the list of candidates to be selected for the next turn.
            Defaults to False. The model may still select the previous speaker -- a warning will be logged if this happens.
        max_selector_attempts (int, optional): The maximum number of attempts to select a speaker using the model. Defaults to 3.
            If the model fails to select a speaker after the maximum number of attempts, the previous speaker will be used if available,
            otherwise the first participant will be used.
        selector_func (Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], str | None], Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[str | None]], optional): A custom selector
            function that takes the conversation history and returns the name of the next speaker.
            If provided, this function will be used to override the model to select the next speaker.
            If the function returns None, the model will be used to select the next speaker.
            NOTE: `selector_func` is not serializable and will be ignored during serialization and deserialization process.
        candidate_func (Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], List[str]], Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], Awaitable[List[str]]], optional):
            A custom function that takes the conversation history and returns a filtered list of candidates for the next speaker
            selection using model. If the function returns an empty list or `None`, `SelectorGroupChat` will raise a `ValueError`.
            This function is only used if `selector_func` is not set. The `allow_repeated_speaker` will be ignored if set.
        custom_message_types (List[type[BaseAgentEvent | BaseChatMessage]], optional): A list of custom message types that will be used in the group chat.
            If you are using custom message types or your agents produces custom message types, you need to specify them here.
            Make sure your custom message types are subclasses of :class:`~autogen_agentchat.messages.BaseAgentEvent` or :class:`~autogen_agentchat.messages.BaseChatMessage`.
        emit_team_events (bool, optional): Whether to emit team events through :meth:`BaseGroupChat.run_stream`. Defaults to False.
        model_client_streaming (bool, optional): Whether to use streaming for the model client. (This is useful for reasoning models like QwQ). Defaults to False.
        model_context (ChatCompletionContext | None, optional): The model context for storing and retrieving
            :class:`~autogen_core.models.LLMMessage`. It can be preloaded with initial messages. Messages stored in model context will be used for speaker selection. The initial messages will be cleared when the team is reset.

    Raises:
        ValueError: If the number of participants is less than two or if the selector prompt is invalid.

    Examples:

    A team with multiple participants:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                async def lookup_hotel(location: str) -> str:
                    return f"Here are some hotels in {location}: hotel1, hotel2, hotel3."

                async def lookup_flight(origin: str, destination: str) -> str:
                    return f"Here are some flights from {origin} to {destination}: flight1, flight2, flight3."

                async def book_trip() -> str:
                    return "Your trip is booked!"

                travel_advisor = AssistantAgent(
                    "Travel_Advisor",
                    model_client,
                    tools=[book_trip],
                    description="Helps with travel planning.",
                )
                hotel_agent = AssistantAgent(
                    "Hotel_Agent",
                    model_client,
                    tools=[lookup_hotel],
                    description="Helps with hotel booking.",
                )
                flight_agent = AssistantAgent(
                    "Flight_Agent",
                    model_client,
                    tools=[lookup_flight],
                    description="Helps with flight booking.",
                )
                termination = TextMentionTermination("TERMINATE")
                team = SelectorGroupChat(
                    [travel_advisor, hotel_agent, flight_agent],
                    model_client=model_client,
                    termination_condition=termination,
                )
                await Console(team.run_stream(task="Book a 3-day trip to new york."))


            asyncio.run(main())

    A team with a custom selector function:

        .. code-block:: python

            import asyncio
            from typing import Sequence
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.ui import Console
            from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                def check_calculation(x: int, y: int, answer: int) -> str:
                    if x + y == answer:
                        return "Correct!"
                    else:
                        return "Incorrect!"

                agent1 = AssistantAgent(
                    "Agent1",
                    model_client,
                    description="For calculation",
                    system_message="Calculate the sum of two numbers",
                )
                agent2 = AssistantAgent(
                    "Agent2",
                    model_client,
                    tools=[check_calculation],
                    description="For checking calculation",
                    system_message="Check the answer and respond with 'Correct!' or 'Incorrect!'",
                )

                def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
                    if len(messages) == 1 or messages[-1].to_text() == "Incorrect!":
                        return "Agent1"
                    if messages[-1].source == "Agent1":
                        return "Agent2"
                    return None

                termination = TextMentionTermination("Correct!")
                team = SelectorGroupChat(
                    [agent1, agent2],
                    model_client=model_client,
                    selector_func=selector_func,
                    termination_condition=termination,
                )

                await Console(team.run_stream(task="What is 1 + 1?"))


            asyncio.run(main())

    A team with custom model context:

        .. code-block:: python

            import asyncio

            from autogen_core.model_context import BufferedChatCompletionContext
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.teams import SelectorGroupChat
            from autogen_agentchat.ui import Console


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")
                model_context = BufferedChatCompletionContext(buffer_size=5)

                async def lookup_hotel(location: str) -> str:
                    return f"Here are some hotels in {location}: hotel1, hotel2, hotel3."

                async def lookup_flight(origin: str, destination: str) -> str:
                    return f"Here are some flights from {origin} to {destination}: flight1, flight2, flight3."

                async def book_trip() -> str:
                    return "Your trip is booked!"

                travel_advisor = AssistantAgent(
                    "Travel_Advisor",
                    model_client,
                    tools=[book_trip],
                    description="Helps with travel planning.",
                )
                hotel_agent = AssistantAgent(
                    "Hotel_Agent",
                    model_client,
                    tools=[lookup_hotel],
                    description="Helps with hotel booking.",
                )
                flight_agent = AssistantAgent(
                    "Flight_Agent",
                    model_client,
                    tools=[lookup_flight],
                    description="Helps with flight booking.",
                )
                termination = TextMentionTermination("TERMINATE")
                team = SelectorGroupChat(
                    [travel_advisor, hotel_agent, flight_agent],
                    model_client=model_client,
                    termination_condition=termination,
                    model_context=model_context,
                )
                await Console(team.run_stream(task="Book a 3-day trip to new york."))


            asyncio.run(main())
    """

    component_config_schema = SelectorGroupChatConfig
    component_provider_override = "autogen_agentchat.teams.SelectorGroupChat"

    DEFAULT_NAME = "SelectorGroupChat"
    DEFAULT_DESCRIPTION = "A team of agents."

    def __init__(
        self,
        participants: List[ChatAgent | Team],
        model_client: ChatCompletionClient,
        *,
        name: str | None = None,
        description: str | None = None,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        selector_prompt: str = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
""",
        allow_repeated_speaker: bool = False,
        max_selector_attempts: int = 3,
        selector_func: Optional[SelectorFuncType] = None,
        candidate_func: Optional[CandidateFuncType] = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
        emit_team_events: bool = False,
        model_client_streaming: bool = False,
        model_context: ChatCompletionContext | None = None,
        agent_input_queue: Any | None = None,
        enable_state_context: bool = True,
        user_proxy_name: str = "user_proxy",
        initial_handoff_context: str | None = None,
        initial_state_of_run: str | None = None,
        state_model_client: ChatCompletionClient | None = None,
    ):
        super().__init__(
            name=name or self.DEFAULT_NAME,
            description=description or self.DEFAULT_DESCRIPTION,
            participants=participants,
            group_chat_manager_name="SelectorGroupChatManager",
            group_chat_manager_class=SelectorGroupChatManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            custom_message_types=custom_message_types,
            emit_team_events=emit_team_events,
            agent_input_queue=agent_input_queue,
        )
        # Validate the participants.
        if len(participants) < 2:
            raise ValueError("At least two participants are required for SelectorGroupChat.")
        self._selector_prompt = selector_prompt
        self._model_client = model_client
        self._state_model_client = state_model_client
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func
        self._max_selector_attempts = max_selector_attempts
        self._candidate_func = candidate_func
        self._model_client_streaming = model_client_streaming
        self._model_context = model_context
        self._enable_state_context = enable_state_context
        self._user_proxy_name = user_proxy_name
        self._initial_handoff_context = initial_handoff_context
        self._initial_state_of_run = initial_state_of_run

    def _create_group_chat_manager_factory(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        agent_input_queue: Any | None = None,
    ) -> Callable[[], BaseGroupChatManager]:
        return lambda: SelectorGroupChatManager(
            name,
            group_topic_type,
            output_topic_type,
            participant_topic_types,
            participant_names,
            participant_descriptions,
            output_message_queue,
            termination_condition,
            max_turns,
            message_factory,
            self._model_client,
            self._selector_prompt,
            self._allow_repeated_speaker,
            self._selector_func,
            self._max_selector_attempts,
            self._candidate_func,
            self._emit_team_events,
            self._model_context,
            self._model_client_streaming,
            agent_input_queue=agent_input_queue,
            enable_state_context=self._enable_state_context,
            user_proxy_name=self._user_proxy_name,
            initial_handoff_context=self._initial_handoff_context,
            initial_state_of_run=self._initial_state_of_run,
            state_model_client=self._state_model_client,
        )

    def _to_config(self) -> SelectorGroupChatConfig:
        return SelectorGroupChatConfig(
            name=self._name,
            description=self._description,
            participants=[participant.dump_component() for participant in self._participants],
            model_client=self._model_client.dump_component(),
            termination_condition=self._termination_condition.dump_component() if self._termination_condition else None,
            max_turns=self._max_turns,
            selector_prompt=self._selector_prompt,
            allow_repeated_speaker=self._allow_repeated_speaker,
            max_selector_attempts=self._max_selector_attempts,
            # selector_func=self._selector_func.dump_component() if self._selector_func else None,
            emit_team_events=self._emit_team_events,
            model_client_streaming=self._model_client_streaming,
            model_context=self._model_context.dump_component() if self._model_context else None,
        )

    @classmethod
    def _from_config(cls, config: SelectorGroupChatConfig) -> Self:
        participants: List[ChatAgent | Team] = []
        for participant in config.participants:
            if participant.component_type == ChatAgent.component_type:
                participants.append(ChatAgent.load_component(participant))
            elif participant.component_type == Team.component_type:
                participants.append(Team.load_component(participant))
            else:
                raise ValueError(
                    f"Invalid participant component type: {participant.component_type}. " "Expected ChatAgent or Team."
                )
        return cls(
            participants=participants,
            model_client=ChatCompletionClient.load_component(config.model_client),
            name=config.name,
            description=config.description,
            termination_condition=TerminationCondition.load_component(config.termination_condition)
            if config.termination_condition
            else None,
            max_turns=config.max_turns,
            selector_prompt=config.selector_prompt,
            allow_repeated_speaker=config.allow_repeated_speaker,
            max_selector_attempts=config.max_selector_attempts,
            # selector_func=ComponentLoader.load_component(config.selector_func, Callable[[Sequence[BaseAgentEvent | BaseChatMessage]], str | None])
            # if config.selector_func
            # else None,
            emit_team_events=config.emit_team_events,
            model_client_streaming=config.model_client_streaming,
            model_context=ChatCompletionContext.load_component(config.model_context) if config.model_context else None,
        )

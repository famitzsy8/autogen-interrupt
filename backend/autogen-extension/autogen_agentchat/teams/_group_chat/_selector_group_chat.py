import asyncio
import logging
import re
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Union, cast

from pydantic import BaseModel, Field
from typing_extensions import Self

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
    UserInputRequestedEvent,
)
from ...state import SelectorManagerState, StateSnapshot
from ._agent_buffer_node_mapping import convert_manager_trim_to_agent_trim
from ._base_group_chat import BaseGroupChat
from ._base_group_chat_manager import BaseGroupChatManager
from ._chat_agent_container import ChatAgentContainer
from .plugins._base import GroupChatPlugin
from ._events import (
    GroupChatAgentResponse,
    GroupChatBranch,
    GroupChatRequestPublish,
    GroupChatStart,
    GroupChatTeamResponse,
    GroupChatTermination,
    SerializableException,
    StateUpdateEvent,
    UserDirectedMessage,
)
from ._node_message_mapping import count_messages_for_node_trim

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
logger = logging.getLogger(__name__)


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
        plugins: list[GroupChatPlugin] | None = None,
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
            plugins=plugins,
        )
        self._model_client = model_client
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

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def reset(self) -> None:
        logger.debug(f"Resetting message thread (previous size: {len(self._message_thread)})")

        self._current_turn = 0
        self._message_thread.clear()
        await self._model_context.clear()
        if self._termination_condition is not None:
            await self._termination_condition.reset()
        self._previous_speaker = None

        logger.debug("Message thread reset successfully")

    async def save_state(self) -> Mapping[str, Any]:
        """Save manager state including plugin states."""
        state = SelectorManagerState(
            message_thread=[msg.dump() for msg in self._message_thread],
            current_turn=self._current_turn,
            previous_speaker=self._previous_speaker,
        )

        result = state.model_dump()

        # Save plugin states
        plugin_states: dict[str, Any] = {}
        for plugin in self._plugins:
            try:
                plugin_state = await plugin.save_state()
                plugin_states[plugin.name] = plugin_state
            except Exception as e:
                logger.warning(f"Plugin '{plugin.name}' failed to save state: {e}", exc_info=True)

        result['plugin_states'] = plugin_states

        return result

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load manager state including plugin states."""
        selector_state = SelectorManagerState.model_validate(state)

        # Existing restoration logic
        self._message_thread = [self._message_factory.create(msg) for msg in selector_state.message_thread]
        await self._add_messages_to_context(
            self._model_context, [msg for msg in self._message_thread if isinstance(msg, BaseChatMessage)]
        )
        self._current_turn = selector_state.current_turn
        self._previous_speaker = selector_state.previous_speaker

        # Load plugin states
        plugin_states = state.get('plugin_states', {})
        for plugin in self._plugins:
            try:
                plugin_state = plugin_states.get(plugin.name)
                if plugin_state is not None:
                    await plugin.load_state(plugin_state)
                    logger.debug(f"Loaded state for plugin '{plugin.name}'")
            except Exception as e:
                logger.warning(f"Plugin '{plugin.name}' failed to load state: {e}", exc_info=True)

    async def _transition_to_next_speakers(self, cancellation_token: CancellationToken) -> None:
        """Select next speaker(s) using plugin hooks and selector logic."""
        # Build participants list
        if self._candidate_func is not None:
            if self._is_candidate_func_async:
                async_candidate_func = cast(AsyncCandidateFunc, self._candidate_func)
                participants = await async_candidate_func(self._message_thread)
            else:
                sync_candidate_func = cast(SyncCandidateFunc, self._candidate_func)
                participants = sync_candidate_func(self._message_thread)
        else:
            # Construct the candidate agent list to be selected from, skip the previous speaker if not allowed.
            if self._previous_speaker is not None and not self._allow_repeated_speaker:
                participants = [p for p in self._participant_names if p != self._previous_speaker]
            else:
                participants = list(self._participant_names)

        # Construct agent roles
        roles = ""
        for topic_type, description in zip(self._participant_names, self._participant_descriptions, strict=True):
            roles += re.sub(r"\s+", " ", f"{topic_type}: {description}").strip() + "\n"
        roles = roles.strip()

        # Check plugins for speaker override BEFORE normal selection
        next_speaker: str | None = None
        for plugin in self._plugins:
            override = await plugin.on_before_speaker_selection(
                self._message_thread, participants, self._participant_names
            )
            if override is not None:
                if override in participants:
                    next_speaker = override
                    break

        # If no plugin override, select using normal selection (AI agents only)
        if next_speaker is None:
            # Filter out user_proxy from candidates - user_proxy can ONLY be selected via plugin override
            # (e.g., when analysis_watchlist triggers)
            ai_only_participants = [p for p in participants if "user_proxy" not in p.lower()]

            if not ai_only_participants:
                raise RuntimeError(
                    f"INVARIANT VIOLATION: No AI agents available for selection. "
                    f"user_proxy can ONLY be selected when analysis triggers. "
                    f"Available participants were: {participants}"
                )

            next_speaker = await self._select_speaker(roles, ai_only_participants, self._max_selector_attempts)

        self._previous_speaker = next_speaker

        # Send request to publish
        speaker_topic_type = self._participant_name_to_topic_type[next_speaker]
        await self.publish_message(
            GroupChatRequestPublish(),
            topic_id=DefaultTopicId(type=speaker_topic_type),
            cancellation_token=cancellation_token,
        )
        self._active_speakers.append(next_speaker)


    def get_current_state_package(self) -> dict[str, Any]:
        """Get current state package from plugins.

        This method aggregates state from all registered plugins by calling their
        `get_state_for_agent()` methods. Later plugins can override keys from
        earlier plugins if they return the same keys.

        Returns:
            Dict with combined state from all plugins.

        This is called by ChatAgentContainer via callback to inject state into agent buffers.
        """
        state: dict[str, Any] = {'participant_names': self._participant_names}

        # Aggregate state from all plugins
        for plugin in self._plugins:
            try:
                plugin_state = plugin.get_state_for_agent()
                state.update(plugin_state)
            except Exception as e:
                logger.warning(f"Plugin '{plugin.name}' failed to provide state for agent: {e}", exc_info=True)

        return state

    @rpc
    async def handle_user_directed_message(self, message: UserDirectedMessage, ctx: MessageContext) -> None:  # type: ignore[override]
        """Handle a user-directed message with trim logic and state recovery.

        Overrides base class to add state snapshot recovery when trimming the message thread.
        """
        self._interrupted = False
        # Clear any lingering active speakers from previous interactions
        self._active_speakers = []
        target = message.target
        trim_up = message.trim_up
        self._old_threads.append(self._message_thread)

        # Handle trim operations with state recovery
        if trim_up > 0:
            logger.info(f"Trimming conversation: removing last {trim_up} nodes")
            logger.debug(f"Before trim - Thread length: {len(self._message_thread)}")

            # Calculate trim amount for manager thread
            messages_to_trim = count_messages_for_node_trim(self._message_thread, trim_up)

            logger.debug(f"Calculated messages_to_trim: {messages_to_trim}")

            # Send individual branch events to each agent with their specific trim value
            # (each agent has a different buffer size depending on when they last spoke)
            for agent_name, agent_topic_type in self._participant_name_to_topic_type.items():
                agent_trim_up = convert_manager_trim_to_agent_trim(self._message_thread, trim_up, agent_name)
                await self.publish_message(
                    GroupChatBranch(agent_trim_up=agent_trim_up),
                    topic_id=DefaultTopicId(type=agent_topic_type),
                    cancellation_token=ctx.cancellation_token,
                )

            # Slice message thread to new length
            self._message_thread = self._message_thread[:-messages_to_trim]

            logger.debug(f"After trim - Thread length: {len(self._message_thread)}")

            # Notify plugins of branch
            new_thread_length = len(self._message_thread)
            for plugin in self._plugins:
                try:
                    await plugin.on_branch(trim_up, new_thread_length)
                except Exception as e:
                    logger.warning(f"Plugin '{plugin.name}' failed to handle branch: {e}", exc_info=True)

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

        # Notify plugins of user message
        if isinstance(message.message, BaseChatMessage):
            for plugin in self._plugins:
                try:
                    await plugin.on_user_message(
                        message.message,
                        is_directed=True,
                        target=target,
                        cancellation_token=ctx.cancellation_token
                    )
                except Exception as e:
                    logger.warning(f"Plugin '{plugin.name}' failed to handle user message: {e}", exc_info=True)

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
        # Only add to active speakers if not already present (avoid duplicates)
        if target not in self._active_speakers:
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
            error = SerializableException.from_exception(e)
            await self._signal_termination_with_error(error)
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
        # Extend the message thread
        self._message_thread.extend(messages)
        base_chat_messages = [m for m in messages if isinstance(m, BaseChatMessage)]
        await self._add_messages_to_context(self._model_context, base_chat_messages)

        # Notify plugins of new messages
        for message in messages:
            # Skip plugin notifications if interrupted
            if self._interrupted:
                return

            for plugin in self._plugins:
                # Check again before each plugin call
                if self._interrupted:
                    return

                try:
                    await plugin.on_message_added(message, self._message_thread, self._cancellation_token)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass  # Continue with other plugins

                # NOTE: Plugins may emit events (like StateUpdateEvent or AnalysisUpdate)
                # These will be handled by checking the return value in future iterations
                # For now, plugins must use callbacks or manager references to emit events

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

        # Aggregate selector state from plugins
        selector_state: dict[str, Any] = {
            "participants": str(participants),
            "roles": roles,
            "history": model_context_history,
        }

        # Let plugins provide state for selector
        for plugin in self._plugins:
            try:
                plugin_selector_state = plugin.get_state_for_selector()
                selector_state.update(plugin_selector_state)
            except Exception as e:
                logger.warning(f"Plugin '{plugin.name}' failed to provide selector state: {e}", exc_info=True)

        select_speaker_prompt = self._selector_prompt.format(**selector_state)

        logger.debug(f"🎯 Selector prompt:\n{select_speaker_prompt[:500]}...")

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
        plugins: list[GroupChatPlugin] | None = None,
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
        self._allow_repeated_speaker = allow_repeated_speaker
        self._selector_func = selector_func
        self._max_selector_attempts = max_selector_attempts
        self._candidate_func = candidate_func
        self._model_client_streaming = model_client_streaming
        self._model_context = model_context
        self._plugins = plugins or []

        # Shared manager holder for state context injection
        # This allows ChatAgentContainers to get state from the manager
        # even though they are created before the manager exists
        self._manager_holder: Dict[str, SelectorGroupChatManager] = {}

    def add_plugin(self, plugin: GroupChatPlugin) -> None:
        """Add a plugin to the team.

        The plugin will be wired up with the manager when the run starts.
        If the manager is already running, the plugin is also registered with the manager.

        Args:
            plugin: The plugin to add
        """
        self._plugins.append(plugin)

        # If manager already exists, register the plugin and wire up event emission
        manager = self._manager_holder.get('manager')
        if manager is not None:
            manager.register_plugin(plugin)
            # Wire up event emission for plugins that support it
            if hasattr(plugin, '_emit_event'):
                mgr = manager  # Capture in local variable for closure
                async def emit_to_queue(event: Any) -> None:
                    try:
                        if mgr._interrupted:
                            return
                        await mgr._output_message_queue.put(event)
                    except Exception:
                        pass
                plugin._emit_event = emit_to_queue

    def get_current_state_package(self) -> Dict[str, Any]:
        """
        Get the current state package from the manager.

        Returns a dictionary containing:
        - state_of_run: Current research progress
        - tool_call_facts: Accumulated facts from tool executions
        - handoff_context: Agent selection rules
        - participant_names: List of participant names

        Returns empty dict if manager is not yet initialized.
        """
        manager = self._manager_holder.get('manager')
        if manager is not None:
            return manager.get_current_state_package()
        return {}

    def get_feedback_context(self) -> Dict[str, Any] | None:
        """
        Get feedback context from the analysis_watchlist plugin if available.

        Returns the pending analysis context when analysis has been triggered
        and is awaiting user feedback. Returns None if no feedback is pending.

        Note: This method clears the pending analysis after retrieval to prevent
        the same context from being sent multiple times.

        Returns:
            Dict with feedback context or None
        """
        for plugin in self._plugins:
            if plugin.name == "analysis_watchlist":
                if hasattr(plugin, 'get_pending_analysis'):
                    pending = plugin.get_pending_analysis()
                    if pending:
                        # Build the feedback context
                        context = {
                            "triggered_components": pending.get("triggered", []),
                            "triggered_with_details": pending.get("triggered_with_details", {}),
                            "scores": {
                                label: {"score": score.score, "reasoning": score.reasoning}
                                for label, score in pending.get("scores", {}).items()
                            },
                            "last_message": {
                                "content": str(pending["message"].content) if pending.get("message") and hasattr(pending["message"], "content") else "",
                                "source": pending["message"].source if pending.get("message") and hasattr(pending["message"], "source") else "unknown",
                            },
                            # Include tool_call_facts and state_of_run for frontend display
                            "tool_call_facts": pending.get("tool_call_facts", ""),
                            "state_of_run": pending.get("state_of_run", ""),
                        }
                        # Clear the pending analysis after retrieval
                        if hasattr(plugin, 'clear_pending_analysis'):
                            plugin.clear_pending_analysis()
                        return context
        return None

    def _create_participant_factory(
        self,
        parent_topic_type: str,
        output_topic_type: str,
        agent: ChatAgent | Team,
        message_factory: MessageFactory,
    ) -> Callable[[], ChatAgentContainer]:
        """Override to inject state context getter into ChatAgentContainer."""
        # Capture references for the closure
        manager_holder = self._manager_holder

        def _state_package_getter() -> Dict[str, Any]:
            """Get state package from manager if available."""
            manager = manager_holder.get('manager')
            if manager is not None:
                return manager.get_current_state_package()
            return {}

        def _factory() -> ChatAgentContainer:
            container = ChatAgentContainer(
                parent_topic_type,
                output_topic_type,
                agent,
                message_factory,
                enable_state_context=True,
                state_package_getter=_state_package_getter,
            )
            return container

        return _factory

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
        def factory() -> BaseGroupChatManager:
            manager = SelectorGroupChatManager(
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
                plugins=self._plugins,
            )

            # Register manager in holder so ChatAgentContainers can access state
            self._manager_holder['manager'] = manager

            # Wire up event emission for plugins that support it
            def wire_plugin_emit(p: GroupChatPlugin, mgr: SelectorGroupChatManager) -> None:
                """Wire up _emit_event for a single plugin."""
                if hasattr(p, '_emit_event'):
                    async def emit_to_queue(event: Any) -> None:
                        try:
                            if mgr._interrupted:
                                return
                            await mgr._output_message_queue.put(event)
                        except Exception:
                            pass
                    p._emit_event = emit_to_queue

            for plugin in self._plugins:
                wire_plugin_emit(plugin, manager)

            return manager
        return factory

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

from autogen_agentchat.teams._group_chat._selector_group_chat import SelectorGroupChatManager, SelectorGroupChat
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from typing import Any, List, Sequence, Callable, Dict, Optional
import asyncio
from autogen_agentchat.base import ChatAgent, Team, TerminationCondition
from autogen_agentchat.teams._group_chat._events import GroupChatTermination
from autogen_agentchat.teams._group_chat._base_group_chat_manager import BaseGroupChatManager
from autogen_agentchat.messages import MessageFactory
from autogen_core import CancellationToken


class HierarchicalGroupChatManager(SelectorGroupChatManager):

    def __init__(
        self,
        allowed_transitions: Optional[Dict[str, List[str]]] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        self.allowed_transitions = allowed_transitions
        super().__init__(*args, **kwargs)
        self.all_speakers = self._participant_names
        self.all_descriptions = self._participant_descriptions
        

    async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str] | str:

        last_speaker = thread[-1].source
        if self.allowed_transitions is None:
            raise ValueError("allowed_transitions cannot be None")
        possible_next_speakers = self.allowed_transitions.get(last_speaker, [])
        possible_next_descriptions = [
            self._participant_descriptions[self.all_speakers.index(speaker)]
            for speaker in possible_next_speakers
        ]

        self._participant_names = possible_next_speakers
        self._participant_descriptions = possible_next_descriptions

        next_speaker = await super().select_speaker(thread)
        return next_speaker
    
    async def _transition_to_next_speakers(self, cancellation_token: CancellationToken) -> None:
        await super()._transition_to_next_speakers(cancellation_token)
        self._participant_names = self.all_speakers
        self._participant_descriptions = self.all_descriptions

class HierarchicalGroupChat(SelectorGroupChat):
    def __init__(
        self,
        allowed_transitions: Dict[str, List[str]],
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.allowed_transitions = allowed_transitions
        self.group_chat_manager_name = "HierarchicalGroupChatManager"
        self.group_chat_manager_class = HierarchicalGroupChatManager

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
        **kwargs: Any,
    ) -> Callable[[], BaseGroupChatManager]:
        return lambda: HierarchicalGroupChatManager(
            self.allowed_transitions,
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
            enable_state_context=self._enable_state_context,  # type: ignore[attr-defined]
            user_proxy_name=self._user_proxy_name,  # type: ignore[attr-defined]
        )



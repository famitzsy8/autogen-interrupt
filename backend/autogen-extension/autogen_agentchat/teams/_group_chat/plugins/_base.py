"""Base protocol for group chat plugins.

This module defines the GroupChatPlugin protocol that allows extending
the behavior of group chat managers with optional functionality.
"""

from typing import Any, Protocol, Sequence, runtime_checkable

from autogen_core import CancellationToken

from ....messages import BaseAgentEvent, BaseChatMessage


@runtime_checkable
class GroupChatPlugin(Protocol):
    """Base protocol for group chat plugins.

    Plugins receive lifecycle hooks from the manager and can:
    - React to messages being added to the thread
    - Influence speaker selection
    - Maintain their own state
    - Inject context into agents and selector prompts
    - Support conversation branching and state recovery

    All methods are called by the BaseGroupChatManager during conversation flow.
    """

    @property
    def name(self) -> str:
        """Unique plugin identifier.

        Returns:
            A string identifier for this plugin, used for state management
            and event routing.
        """
        ...

    async def on_message_added(
        self,
        message: BaseAgentEvent | BaseChatMessage,
        thread: Sequence[BaseAgentEvent | BaseChatMessage],
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Called after a message is added to the thread.

        This hook is invoked after the manager updates its message thread
        with a new message from an agent or user.

        Args:
            message: The message that was just added to the thread.
            thread: The complete message thread including the new message.
            cancellation_token: Optional cancellation token for async operations.

        Use for:
            - Updating internal plugin state based on new messages
            - Creating state snapshots
            - Emitting plugin-specific events
        """
        ...

    async def on_before_speaker_selection(
        self,
        thread: Sequence[BaseAgentEvent | BaseChatMessage],
        candidates: list[str],
        participant_names: list[str],
    ) -> str | None:
        """Called before the manager selects the next speaker.

        This hook allows plugins to override normal speaker selection logic.
        The first plugin to return a non-None value will force that speaker.

        Args:
            thread: The current message thread.
            candidates: List of candidate speaker names for normal selection.
            participant_names: All participant names in the group chat.

        Returns:
            - str: Force this specific speaker (overrides normal selection).
            - None: No override, proceed with normal selection.

        Use for:
            - Injecting user_proxy when analysis triggers
            - Custom routing logic based on conversation state
            - Quality control interventions
        """
        ...

    async def on_user_message(
        self,
        message: BaseChatMessage,
        is_directed: bool,
        target: str | None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Called when a user message is received.

        This hook is invoked when the manager processes a UserDirectedMessage
        event, before the message is routed to the target agent.

        Args:
            message: The user's message.
            is_directed: True if the message was sent to a specific agent.
            target: Target agent name if is_directed is True, otherwise None.
            cancellation_token: Optional cancellation token for async operations.

        Use for:
            - Updating handoff context based on user instructions
            - Detecting intent changes
            - Clearing temporary state (e.g., feedback context)
        """
        ...

    async def on_branch(self, trim_count: int, new_thread_length: int) -> None:
        """Called when the conversation branches (trim operation).

        This hook is invoked when the manager trims messages from the thread
        to implement conversation branching. Plugins should recover state
        to align with the new thread length.

        Args:
            trim_count: Number of messages trimmed from the end of the thread.
            new_thread_length: Length of the thread after trimming.

        Use for:
            - Recovering state snapshots from before the trim point
            - Cleaning up state data that no longer applies
            - Clearing temporary context (e.g., feedback triggers)
        """
        ...

    def get_state_for_agent(self) -> dict[str, Any]:
        """Return state to inject into agent system prompts.

        This method is called by the ChatAgentContainer before each agent
        invocation. The returned dictionary values are made available to
        agent prompts via template variables.

        Returns:
            Dictionary with keys corresponding to prompt template variables.
            Common keys: 'state_of_run', 'tool_call_facts', 'handoff_context'.

        Use for:
            - Providing external memory to agents
            - Injecting context that reduces cognitive load
            - Sharing verified facts across agent invocations
        """
        ...

    def get_state_for_selector(self) -> dict[str, Any]:
        """Return state to inject into selector prompt.

        This method is called by the manager before speaker selection.
        The returned dictionary values are made available to the selector
        prompt template via {key} placeholders.

        Returns:
            Dictionary with keys corresponding to selector prompt template
            variables. Common keys: 'state_of_run', 'handoff_context'.

        Use for:
            - Providing selection context based on conversation progress
            - Injecting user preferences for agent routing
            - Sharing handoff rules with the selector
        """
        ...

    async def save_state(self) -> dict[str, Any]:
        """Save plugin state for persistence.

        This method is called by the manager when saving conversation state.
        The returned dictionary should contain all plugin state needed to
        restore the plugin to its current condition.

        Returns:
            Dictionary containing serializable plugin state.

        Use for:
            - Persisting internal state across sessions
            - Saving state snapshots
            - Supporting conversation export/import
        """
        ...

    async def load_state(self, state: dict[str, Any]) -> None:
        """Load plugin state from persistence.

        This method is called by the manager when restoring conversation state.
        The plugin should restore all internal state from the provided dictionary.

        Args:
            state: Dictionary containing previously saved plugin state.

        Use for:
            - Restoring internal state from saved sessions
            - Loading state snapshots
            - Supporting conversation import
        """
        ...

"""Analysis Watchlist Plugin for hallucination detection and user feedback trigger.

This plugin scores agent messages against trusted facts and triggers user feedback
when scores exceed the threshold, providing quality assurance for research outputs.
"""

from __future__ import annotations
import logging
import uuid
from typing import Any, Callable, Awaitable, Sequence

from autogen_core import CancellationToken

from .....messages import BaseAgentEvent, BaseChatMessage, TextMessage, ToolCallSummaryMessage
from ._service import AnalysisService
from ._models import AnalysisComponent, ComponentScore, AnalysisUpdate

logger = logging.getLogger(__name__)


class AnalysisWatchlistPlugin:
    """
    Hallucination detection and user feedback trigger.

    Scores agent messages against trusted facts (from external state)
    and triggers user feedback when score exceeds threshold.

    This provides quality assurance by catching potential hallucinations
    before they propagate through the conversation.
    """

    def __init__(
        self,
        analysis_service: AnalysisService,
        components: list[AnalysisComponent],
        trigger_threshold: int = 8,
        state_getter: Callable[[], dict[str, str]] | None = None,
        feedback_callback: Callable[[dict[str, Any]], None] | None = None,
        user_proxy_name: str = "user_proxy",
    ) -> None:
        """
        Initialize the analysis watchlist plugin.

        Args:
            analysis_service: Service for scoring messages against components
            components: List of analysis components to score against
            trigger_threshold: Score threshold (1-10) for triggering user feedback
            state_getter: Optional callback to get external state (tool_call_facts, state_of_run)
            feedback_callback: Optional callback when threshold is exceeded
            user_proxy_name: Name of user proxy agent (messages from this source are skipped)
        """
        self._service = analysis_service
        self._components = components
        self._threshold = trigger_threshold
        self._state_getter = state_getter
        self._feedback_callback = feedback_callback
        self._user_proxy_name = user_proxy_name

        # Track pending analysis results that should trigger feedback
        self._pending_analysis: dict[str, Any] | None = None

        # Event emitter callback (set by manager)
        self._emit_event: Callable[[Any], Awaitable[None]] | None = None

        logger.info(
            f"AnalysisWatchlistPlugin initialized with {len(components)} components, "
            f"threshold={trigger_threshold}"
        )

    @property
    def name(self) -> str:
        """Unique plugin identifier."""
        return "analysis_watchlist"

    async def on_message_added(
        self,
        message: BaseAgentEvent | BaseChatMessage,
        thread: Sequence[BaseAgentEvent | BaseChatMessage],
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """
        Score TextMessages and emit AnalysisUpdate events.

        Called after a message is added to the thread. Analyzes TextMessage instances
        and emits scoring results to the frontend.

        Args:
            message: The message that was just added
            thread: The complete message thread
            cancellation_token: Optional cancellation token
        """
        # Only analyze BaseChatMessage instances (TextMessage, ToolCallSummaryMessage, etc.)
        # Skip events like ThoughtEvent, ToolCallRequestEvent, ToolCallExecutionEvent
        if not isinstance(message, BaseChatMessage):
            return

        # Skip if no components configured
        if not self._components:
            return

        # Skip user messages (user feedback should not be analyzed)
        if message.source == self._user_proxy_name or message.source == "You" or message.source == "user":
            return

        try:
            # Get external state if available
            external_state = self._state_getter() if self._state_getter else {}
            tool_call_facts = external_state.get("tool_call_facts", "")
            state_of_run = external_state.get("state_of_run", "")

            # Extract message content (handle different content types)
            message_content = (
                message.content
                if isinstance(message.content, str)
                else str(message.content)
            )

            # Score the message
            scores = await self._service.score_message(
                message=message_content,
                components=self._components,
                tool_call_facts=tool_call_facts,
                state_of_run=state_of_run,
                trigger_threshold=self._threshold,
            )

            # Get message node_id (use 'id' attribute if available, else generate UUID)
            node_id = getattr(message, "id", str(uuid.uuid4()))

            # Identify triggered components
            triggered_components = [
                label for label, score_obj in scores.items()
                if score_obj.score >= self._threshold
            ]

            # Emit AnalysisUpdate event to frontend
            if self._emit_event:
                analysis_event = AnalysisUpdate(
                    node_id=node_id,
                    scores=scores,
                    triggered_components=triggered_components,
                )
                await self._emit_event(analysis_event)

            # Store pending analysis for potential feedback trigger
            if triggered_components:
                # Build triggered components with their descriptions and scores
                triggered_with_details = {}
                for label in triggered_components:
                    component = next(
                        (c for c in self._components if c.label == label),
                        None,
                    )
                    if component:
                        triggered_with_details[label] = {
                            "description": component.description,
                            "score": scores[label].score,
                            "reasoning": scores[label].reasoning,
                        }

                # Store pending analysis
                self._pending_analysis = {
                    "node_id": node_id,
                    "triggered": triggered_components,
                    "triggered_with_details": triggered_with_details,
                    "scores": scores,
                    "message": message,
                    "tool_call_facts": tool_call_facts,
                    "state_of_run": state_of_run,
                }

                # Notify via callback if provided
                if self._feedback_callback:
                    self._feedback_callback(self._pending_analysis)

        except Exception as e:
            logger.warning(
                f"Analysis scoring failed: {e}, continuing without analysis",
                exc_info=True,
            )

    async def on_before_speaker_selection(
        self,
        thread: Sequence[BaseAgentEvent | BaseChatMessage],
        candidates: list[str],
        participant_names: list[str],
    ) -> str | None:
        """
        Override speaker selection when analysis has been triggered.

        When analysis triggers (pending_analysis exists), this method returns
        the user_proxy name to inject the user into the conversation for feedback.

        Args:
            thread: Current message thread
            candidates: Candidate speaker names
            participant_names: All participant names

        Returns:
            user_proxy name if analysis triggered, None otherwise
        """
        if self._pending_analysis:
            return self._user_proxy_name
        return None

    async def on_user_message(
        self,
        message: BaseChatMessage,
        is_directed: bool,
        target: str | None,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """
        Clear pending analysis when user provides feedback.

        Args:
            message: The user's message
            is_directed: True if directed to specific agent
            target: Target agent name if directed
            cancellation_token: Optional cancellation token
        """
        if self._pending_analysis:
            self._pending_analysis = None

    async def on_branch(self, trim_count: int, new_thread_length: int) -> None:
        """
        Clear pending analysis on branch.

        Args:
            trim_count: Number of messages trimmed
            new_thread_length: Length after trim
        """
        if self._pending_analysis:
            self._pending_analysis = None

    def get_state_for_agent(self) -> dict[str, Any]:
        """
        Analysis plugin doesn't inject state into agents.

        Returns:
            Empty dict
        """
        return {}

    def get_state_for_selector(self) -> dict[str, Any]:
        """
        Analysis plugin doesn't inject state into selector.

        Returns:
            Empty dict
        """
        return {}

    async def save_state(self) -> dict[str, Any]:
        """
        Persist plugin state.

        Returns:
            Dict containing plugin state (components, threshold)
        """
        return {
            "components": [c.model_dump() for c in self._components],
            "threshold": self._threshold,
        }

    async def load_state(self, state: dict[str, Any]) -> None:
        """
        Restore plugin state.

        Args:
            state: Previously saved plugin state
        """
        if "components" in state:
            self._components = [
                AnalysisComponent.model_validate(c) for c in state["components"]
            ]
            logger.info(f"Loaded {len(self._components)} analysis components")

        if "threshold" in state:
            self._threshold = state["threshold"]
            logger.info(f"Loaded analysis threshold: {self._threshold}")

    def get_pending_analysis(self) -> dict[str, Any] | None:
        """
        Get pending analysis context for feedback.

        This method is called by the manager or feedback handler to retrieve
        details about triggered analysis.

        Returns:
            Pending analysis dict or None if no trigger pending
        """
        return self._pending_analysis

    def clear_pending_analysis(self) -> None:
        """Clear pending analysis context."""
        self._pending_analysis = None

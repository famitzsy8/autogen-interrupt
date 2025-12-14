from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ChatMessage,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    SelectorEvent,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
    UserInputRequestedEvent,
)
from autogen_agentchat.teams._group_chat._events import StateUpdateEvent
from autogen_agentchat.teams._group_chat.plugins.analysis_watchlist import (
    AnalysisService,
    AnalysisComponent,
    AnalysisUpdate,
    AnalysisWatchlistPlugin,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient
from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocket, WebSocketState

from factory.team_factory import AgentTeamContext, init_team
from handlers.agent_input_queue import AgentInputQueue
from handlers.session_manager import get_session_manager, Session
from handlers.state_manager import StateManager
from models import (
    AgentDetails,
    AgentInputRequest,
    AgentMessage,
    AgentTeamNames,
    AnalysisComponentsInit,
    ComponentGenerationRequest,
    ComponentGenerationResponse,
    ErrorMessage,
    HumanInputResponse,
    InterruptAcknowledged,
    MessageType,
    ParticipantNames,
    RunConfig,
    RunStartConfirmed,
    RunTermination,
    StateUpdate,
    StreamEnd,
    TerminateAck,
    TerminateRequest,
    ToolCall,
    ToolCallInfo,
    ToolExecution,
    ToolExecutionResult,
    TreeUpdate,
    UserDirectedMessage,
    UserInterrupt,
)
from utils.summarization import init_summarizer, summarize_message
from utils.yaml_utils import get_agent_details, get_agent_team_names, get_summarization_system_prompt, get_team_main_tasks

logger = logging.getLogger(__name__)


class WebSocketHandler:

    # Handles the WebSocket connections for the agent team

    def __init__(self, websocket: WebSocket) -> None:

        self.websocket = websocket
        self.session: Session | None = None
        self.session_manager = get_session_manager()
        self.agent_input_queue = AgentInputQueue()
        self.agent_input_queue.websocket_handler = self
        self.agent_team_config: RunConfig | None = None
        self.current_tool_call_node_id: str | None = None
        self._pending_agent_messages: list[AgentMessage] = []
    
    async def handle_connection(self) -> None:
        await self.websocket.accept()

        try:
            team_names = get_agent_team_names()
            await self._send_agent_team_names(team_names)
            await self._send_agent_details()

            while True:
                message_data = await self.websocket.receive_text()
                message_dict = json.loads(message_data)
                message_type = message_dict.get('type')

                if message_type == MessageType.COMPONENT_GENERATION_REQUEST:
                    await self._handle_component_generation(message_dict)

                elif message_type == MessageType.RUN_START_CONFIRMED:
                    self.agent_team_config = RunStartConfirmed(**message_dict)
                    break

                elif message_type == MessageType.START_RUN:
                    self.agent_team_config = RunConfig(**message_dict)
                    break

                else:
                    await self._send_error("INVALID_MESSAGE_TYPE", f"Unexpected message type: {message_type}")
                    continue

            session_id = self.agent_team_config.session_id
            state_file = Path(os.getenv("STATE_FILE_PATH", f"agent_run_state_{session_id}.json"))

            self.session = self.session_manager.get_or_create_session(
                session_id=session_id,
                state_file_path=str(state_file)
            )

            self.session.add_websocket(self.websocket)

            if self.session.agent_team_context is None:
                await self._initialize_run()
                await self._send_participant_names()

                initial_topic = self.agent_team_config.initial_topic or get_team_main_tasks()

                if self.agent_team_config.company_name and self.agent_team_config.bill_name and self.agent_team_config.congress:
                    initial_topic = initial_topic.format(
                        company_name=self.agent_team_config.company_name,
                        bill_name=self.agent_team_config.bill_name,
                        bill=self.agent_team_config.bill_name,
                        year=self.agent_team_config.congress,
                        congress=self.agent_team_config.congress
                    )

                self.session.state_manager.initialize_root(
                    agent_name="You", message=initial_topic
                )

                await self._broadcast_tree_update()
                await self._conversation_stream(initial_topic)
            else:
                await self._send_tree_update()

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            await self._send_error("CONFIG_JSON_ERROR", f"Invalid JSON: {str(e)}")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            await self._send_error("CONFIG_VALIDATION_ERROR", str(e))
        except WebSocketDisconnect:
            pass
        except RuntimeError as e:
            # Handle WebSocket "not connected" errors gracefully
            if "not connected" in str(e).lower():
                logger.debug(f"WebSocket disconnected: {e}")
            else:
                logger.error(f"Runtime error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Handler error: {type(e).__name__}: {e}", exc_info=True)
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self._send_error("HANDLER_ERROR", str(e))


        finally:
            await self._cleanup()


    async def _handle_component_generation(self, request_dict: dict) -> None:
        """Generate analysis components from user prompt without starting run."""
        try:
            request = ComponentGenerationRequest(**request_dict)

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set in environment")

            temp_client = OpenAIChatCompletionClient(
                model="gpt-4o-mini",
                api_key=api_key
            )

            analysis_service = AnalysisService(model_client=temp_client)
            components = await analysis_service.parse_prompt(request.analysis_prompt)

            response = ComponentGenerationResponse(
                type=MessageType.COMPONENT_GENERATION_RESPONSE,
                components=components,
                timestamp=datetime.now()
            )

            await self.websocket.send_text(response.model_dump_json())

        except Exception as e:
            logger.error(f"Component generation failed: {e}", exc_info=True)
            response = ComponentGenerationResponse(
                type=MessageType.COMPONENT_GENERATION_RESPONSE,
                components=[],
                timestamp=datetime.now()
            )
            await self.websocket.send_text(response.model_dump_json())

    async def _initialize_run(self) -> None:
        if not self.session:
            raise RuntimeError("Session not initialized")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")

        summarization_prompt = get_summarization_system_prompt()
        init_summarizer(api_key=api_key, model="gpt-4o-mini", system_prompt=summarization_prompt)

        self.session.agent_team_context = await init_team(
            api_key=api_key,
            agent_input_queue=self.agent_input_queue,
            company_name=self.agent_team_config.company_name,
            bill_name=self.agent_team_config.bill_name,
            congress=self.agent_team_config.congress
        )

        self.session.state_manager.display_names = self.session.agent_team_context.display_names

        approved_components = []
        trigger_threshold = 8

        if isinstance(self.agent_team_config, RunStartConfirmed):
            approved_components = self.agent_team_config.approved_components
            trigger_threshold = self.agent_team_config.trigger_threshold

        elif isinstance(self.agent_team_config, RunConfig) and self.agent_team_config.analysis_prompt:
            model_client = self.session.agent_team_context.team._model_client
            analysis_service = AnalysisService(model_client=model_client)

            try:
                approved_components = await analysis_service.parse_prompt(
                    self.agent_team_config.analysis_prompt
                )
                trigger_threshold = self.agent_team_config.trigger_threshold
            except Exception as e:
                logger.error(f"Failed to parse prompt in legacy mode: {e}", exc_info=True)
                approved_components = []

        if approved_components:
            # Create analysis service for component generation and session storage
            model_client = self.session.agent_team_context.team._model_client
            analysis_service = AnalysisService(model_client=model_client)

            # Store for the session (used for component generation and tracking)
            self.session.analysis_service = analysis_service
            self.session.active_components = approved_components
            self.session.trigger_threshold = trigger_threshold

            # Create state getter to provide state to the analysis plugin
            def state_getter() -> dict[str, str]:
                state_pkg = self.session.agent_team_context.team.get_current_state_package()
                return {
                    "tool_call_facts": state_pkg.get("tool_call_facts", ""),
                    "state_of_run": state_pkg.get("state_of_run", ""),
                }

            # Find the actual user_proxy name from participants
            user_proxy_name = next(
                (name for name in self.session.agent_team_context.participant_names
                 if "user_proxy" in name.lower()),
                "user_proxy"  # fallback
            )

            # Create AnalysisWatchlistPlugin and add to team
            analysis_plugin = AnalysisWatchlistPlugin(
                analysis_service=analysis_service,
                components=approved_components,
                trigger_threshold=trigger_threshold,
                state_getter=state_getter,
                user_proxy_name=user_proxy_name,
            )

            # Add plugin to team (will be wired up with event emission)
            self.session.agent_team_context.team.add_plugin(analysis_plugin)

            init_message = AnalysisComponentsInit(
                type="analysis_components_init",
                components=approved_components,
                timestamp=datetime.now(timezone.utc)
            )

            await self.session_manager.broadcast_to_session(
                session_id=self.session.session_id,
                message=init_message.model_dump_json()
            )

    async def _conversation_stream(self, initial_topic: str) -> None:
        if not self.session or not self.session.agent_team_context or not self.session.state_manager:
            raise RuntimeError("Session, agent team context or state manager not initialized")

        stream = self.session.agent_team_context.team.run_stream(task=initial_topic)
        message_task = asyncio.create_task(stream.__anext__())

        # Only create client task if WebSocket is still connected
        client_task: asyncio.Task[str] | None = None
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                client_task = asyncio.create_task(self.websocket.receive_text())
            except RuntimeError as e:
                logger.warning(f"Failed to create initial client task: {e}")
                client_task = None

        try:
            while True:
                pending: set[asyncio.Task[object]] = {message_task}
                if client_task is not None:
                    pending.add(client_task)

                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                if message_task in done:
                    try:
                        message = message_task.result()
                    except StopAsyncIteration:
                        await self._send_stream_end("Run completed")
                        if client_task is not None and client_task.done():
                            await self._process_client_command(client_task)
                        break
                    except asyncio.CancelledError:
                        message_task = asyncio.create_task(stream.__anext__())
                        continue
                    except Exception as e:
                        logger.warning(f"Stream error (non-fatal): {type(e).__name__}: {str(e)[:100]}")
                        message_task = asyncio.create_task(stream.__anext__())
                        continue

                    if isinstance(message, StopMessage):
                        await self._process_stop_message(message)

                    elif isinstance(message, BaseChatMessage):
                        if message.source == "You":
                            message_task = asyncio.create_task(stream.__anext__())
                            continue
                        await self._process_agent_message(message)

                    elif isinstance(message, ToolCallRequestEvent):
                        await self._send_tool_calls_request(message)

                    elif isinstance(message, ToolCallExecutionEvent):
                        await self._send_tool_calls_execution(message)

                    elif isinstance(message, StateUpdateEvent):
                        await self._send_state_update(message)

                    elif isinstance(message, SelectorEvent):
                        pass  # Selector events are internal

                    elif isinstance(message, UserInputRequestedEvent):
                        pass  # Handled via agent input queue

                    elif isinstance(message, AnalysisUpdate):
                        await self._send_analysis_update(message)

                    elif hasattr(message, "stop_reason"):
                        await self._send_stream_end(str(message.stop_reason))
                        if client_task is not None and client_task.done():
                            await self._process_client_command(client_task)
                        break

                    message_task = asyncio.create_task(stream.__anext__())

                if client_task is not None and client_task in done:
                    client_task = await self._process_client_command(client_task)
                    if client_task is None:
                        # WebSocket disconnected, stop processing
                        break

                # If we have no client task and WebSocket is disconnected, exit
                if client_task is None and self.websocket.client_state != WebSocketState.CONNECTED:
                    logger.info("WebSocket disconnected, stopping conversation stream")
                    break

        except asyncio.CancelledError:
            raise
        finally:
            for task in [message_task, client_task]:
                if task is not None and not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
    
    async def _process_client_command(
        self, client_task: asyncio.Task[str]
    ) -> asyncio.Task[str] | None:
        try:
            raw_message = client_task.result()
        except asyncio.CancelledError:
            return None
        except (EOFError, WebSocketDisconnect):
            return None
        except RuntimeError as exc:
            # WebSocket disconnected
            if "not connected" in str(exc).lower():
                return None
            logger.error(f"Client message failed: {exc}", exc_info=True)
            return None
        except Exception as exc:
            logger.error(f"Client message failed: {exc}", exc_info=True)
            # Check if WebSocket is still connected before creating new task
            if self.websocket.client_state != WebSocketState.CONNECTED:
                return None
            try:
                return asyncio.create_task(self.websocket.receive_text())
            except RuntimeError:
                return None

        try:
            message_dict = json.loads(raw_message)
            message_type = message_dict.get("type")

            if message_type == MessageType.USER_INTERRUPT:
                await self._handle_interrupt(message_dict)
            elif message_type == MessageType.HUMAN_INPUT_RESPONSE:
                await self._handle_human_input_response(message_dict)
            elif message_type == MessageType.USER_DIRECTED_MESSAGE:
                await self._handle_user_message(message_dict)
            elif message_type == MessageType.TERMINATE_REQUEST:
                await self._handle_terminate_request(message_dict)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode client message: {e}")
        except Exception as e:
            logger.error(f"Error processing client message: {e}")
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self._send_error("MESSAGE_PROCESSING_ERROR", str(e))

        # Check if WebSocket is still connected before creating new task
        if self.websocket.client_state != WebSocketState.CONNECTED:
            return None
        try:
            return asyncio.create_task(self.websocket.receive_text())
        except RuntimeError as e:
            # WebSocket may have disconnected between state check and task creation
            logger.debug(f"Failed to create receive task: {e}")
            return None
    
    async def _handle_interrupt(self, message_dict: dict[str, Any]) -> None:
        try:
            interrupt_msg = UserInterrupt(**message_dict)

            if not self.session.agent_team_context:
                raise RuntimeError("Agent team context not initialized")

            await self.session.agent_team_context.user_control.interrupt(self.session.agent_team_context.team)
            await self._send_interrupt_acknowledged()

        except Exception as e:
            logger.error(f"Interrupt error: {e}", exc_info=True)
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self._send_error("INTERRUPT_ERROR", str(e))

    async def _handle_terminate_request(self, message_dict: dict[str, Any]) -> None:
        """Handle user-initiated termination request."""
        try:
            if not self.session or not self.session.agent_team_context:
                raise RuntimeError("Agent team context not initialized")

            team = self.session.agent_team_context.team
            external_termination = self.session.agent_team_context.external_termination

            state_pkg = team.get_current_state_package()
            last_text_msg = self._find_last_text_message()

            external_termination.set()

            ack = TerminateAck(
                state_of_run=state_pkg.get('state_of_run', ''),
                tool_call_facts=state_pkg.get('tool_call_facts', ''),
                last_message_content=last_text_msg.content if last_text_msg else '',
                last_message_source=last_text_msg.source if last_text_msg else ''
            )

            if self.websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await self.websocket.send_text(ack.model_dump_json())
                except RuntimeError:
                    pass  # WebSocket disconnected during send

        except Exception as e:
            logger.error(f"Terminate error: {e}", exc_info=True)
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self._send_error("TERMINATE_ERROR", str(e))

    def _find_last_text_message(self) -> TextMessage | None:
        """Find the last TextMessage in the conversation."""
        try:
            if not self.session or not self.session.agent_team_context:
                return None

            team = self.session.agent_team_context.team
            manager_holder = getattr(team, '_manager_holder', None)
            if not manager_holder:
                return None

            manager = manager_holder.get('manager')
            if not manager:
                return None

            message_thread = getattr(manager, '_message_thread', [])

            for msg in reversed(message_thread):
                if isinstance(msg, TextMessage):
                    return msg

            return None
        except Exception:
            return None

    async def _handle_user_message(self, message_dict: dict[str, Any]) -> None:
        try:
            user_message = UserDirectedMessage(**message_dict)

            if not self.session.agent_team_context:
                await self._send_error(
                    "NO_AGENT_TEAM_CONTEXT",
                    "Agent team context not initialized",
                )
                return

            if user_message.target_agent not in self.session.agent_team_context.participant_names:
                await self._send_error(
                    "INVALID_TARGET_AGENT",
                    f"Agent '{user_message.target_agent}' not found. "
                    f"Valid agents: {', '.join(self.session.agent_team_context.participant_names)}",
                )
                return

            if "user_proxy" in user_message.target_agent.lower():
                await self._send_error(
                    "INVALID_TARGET_AGENT",
                    f"Cannot send messages to '{user_message.target_agent}' as it represents the user. "
                    f"Please select a different agent.",
                )
                return

            user_node = self.session.state_manager.create_branch(
                trim_count=user_message.trim_count,
                user_message=user_message.content
            )

            self.session.state_manager.save_to_file()
            await self._send_tree_update()

            result: TaskResult = await self.session.agent_team_context.user_control.send(
                self.session.agent_team_context.team,
                user_message.content,
                user_message.target_agent,
                trim_up=user_message.trim_count,
            )

            if result and getattr(result, "messages", None):
                for response in result.messages:
                    if isinstance(response, BaseChatMessage) and response.source == "You":
                        continue

                    if isinstance(response, (TextMessage, StopMessage, ToolCallSummaryMessage, HandoffMessage)):
                        if hasattr(response, "content"):
                            await self._process_agent_message(response)

        except Exception as e:
            logger.error(f"Error handling user message: {e}", exc_info=True)
            await self._send_error("USER_MESSAGE_ERROR", str(e))

            with contextlib.suppress(Exception):
                await self.session.agent_team_context.team.resume()
    
    async def _process_agent_message(self, message: ChatMessage) -> None:
        if not self.session.state_manager:
            raise RuntimeError("State manager not initialized")

        agent_name = message.source if hasattr(message, "source") else "Unknown"
        content = str(message.content)

        summary = await summarize_message(agent_name=agent_name, message_content=content)
        msg_id = getattr(message, "id", None)

        # Create a new node for this message with summary
        node = self.session.state_manager.add_node(
            agent_name=agent_name,
            message=content,
            summary=summary,
            node_id=msg_id
        )
        if node is None:
            return

        node_id = node.id
        self.session.state_manager.save_to_file()

        agent_msg = AgentMessage(
            agent_name=agent_name,
            content=content,
            summary=summary,
            node_id=node_id
        )

        if agent_name == "You":
            await self._send_message(agent_msg)
        else:
            self._pending_agent_messages.append(agent_msg)

    async def _process_stop_message(self, message: StopMessage) -> None:
        """Handle StopMessage by determining if run was interrupted or completed."""
        await self._process_agent_message(message)

        if message.content == "USER_INTERRUPT":
            return

        await self._send_run_termination(
            status="COMPLETED",
            reason=message.content,
            source=message.source
        )

    async def _send_run_termination(self, status: str, reason: str, source: str) -> None:
        """
        Send a RunTermination message to the frontend to notify of run completion.
        """
        termination = RunTermination(
            status=status,
            reason=reason,
            source=source
        )
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(termination.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send
    
    async def _send_agent_team_names(self, team_names: list[str]) -> None:
        # Send available agent team configuration names to frontend
        team_names_msg = AgentTeamNames(agent_team_names=team_names)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(team_names_msg.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _send_agent_details(self) -> None:
        # Send agent details (names and descriptions) to frontend
        agents_data = get_agent_details()
        agent_details_msg = AgentDetails(agents=agents_data)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(agent_details_msg.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _send_participant_names(self) -> None:
        # Send individual agent participant names to frontend for agent selection dropdown
        if not self.session or not self.session.agent_team_context:
            raise RuntimeError("Agent team context not initialized")

        # Filter out user_proxy agents from the participant list
        # These represent the user and shouldn't receive directed messages
        filtered_participants = [
            name for name in self.session.agent_team_context.participant_names
            if "user_proxy" not in name.lower()
        ]

        participant_names_msg = ParticipantNames(
            participant_names=filtered_participants
        )
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(participant_names_msg.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _send_message(self, message: AgentMessage) -> None:
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(message.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _flush_pending_agent_messages(self) -> None:
        if not self._pending_agent_messages:
            return

        pending = self._pending_agent_messages.copy()
        self._pending_agent_messages.clear()

        for queued_message in pending:
            await self._send_message(queued_message)
            await self._send_tree_update()

    async def _send_tree_update(self) -> None:
        """Send tree update to this specific WebSocket connection only."""
        if not self.session.state_manager:
            raise RuntimeError("State manager not initialized")
        if self.session.state_manager.root is None:
            raise RuntimeError("State manager root node is None")

        tree_update = TreeUpdate(
            root=self.session.state_manager.root,
            current_branch_id=self.session.state_manager.current_branch_id
        )

        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(tree_update.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _broadcast_tree_update(self) -> None:
        """Broadcast tree update to all WebSocket connections in this session."""
        if not self.session or not self.session.state_manager:
            raise RuntimeError("Session or state manager not initialized")
        if self.session.state_manager.root is None:
            raise RuntimeError("State manager root node is None")
            return

        tree_update = TreeUpdate(
            root=self.session.state_manager.root,
            current_branch_id=self.session.state_manager.current_branch_id
        )

        # Broadcast to all connections in the session
        await self.session_manager.broadcast_to_session(
            session_id=self.session.session_id,
            message=tree_update.model_dump_json()
        )

    async def _send_interrupt_acknowledged(self) -> None:
        ack = InterruptAcknowledged()
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(ack.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _send_tool_calls_request(self, message: ToolCallRequestEvent) -> None:
        # Check if message has an ID (e.g. from SelectorGroupChat analysis)
        msg_id = getattr(message, "id", None)

        # Create new node for tool call
        node = self.session.state_manager.add_node(
            agent_name=message.source,
            message=message.to_text(),
            node_type="tool_call",
            node_id=msg_id
        )
        self.current_tool_call_node_id = node.id
        self.session.state_manager.save_to_file()
        await self._send_tree_update()

        tool_calls = []
        for tc in message.content:
            tc_info = ToolCallInfo(id=tc.id, name=tc.name, arguments=tc.arguments)
            tool_calls.append(tc_info)
        tc_request = ToolCall(
            agent_name=message.source,
            tools=tool_calls,
            node_id=node.id,
        )

        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(tc_request.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send

    async def _send_analysis_update(self, message: AnalysisUpdate) -> None:
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to send analysis update for node {message.node_id}: {e}")

    async def _send_tool_calls_execution(self, message: ToolCallExecutionEvent) -> None:

        results = []
        for tc_result in message.content:
            result = ToolExecutionResult(
                tool_call_id=tc_result.call_id,
                tool_name=tc_result.name,
                success= not tc_result.is_error,
                result=tc_result.content,
            )
            results.append(result)

        # Only send ToolExecution if we have a valid node_id
        if self.current_tool_call_node_id:
            tc_execution = ToolExecution(
                agent_name=message.source,
                results=results,
                node_id=self.current_tool_call_node_id
            )
            await self._send_tree_update()

            if self.websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await self.websocket.send_text(tc_execution.model_dump_json())
                except RuntimeError:
                    pass  # WebSocket disconnected during send

        self.current_tool_call_node_id = None

    async def _send_state_update(self, message: StateUpdateEvent) -> None:
        state_update = StateUpdate(
            state_of_run=message.state_of_run,
            tool_call_facts=message.tool_call_facts,
            handoff_context=message.handoff_context,
            message_index=message.message_index
        )
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await self.websocket.send_text(state_update.model_dump_json())
                except RuntimeError:
                    pass  # WebSocket disconnected during send
        finally:
            await self._flush_pending_agent_messages()


    async def _send_stream_end(self, reason: str) -> None:
        await self._flush_pending_agent_messages()

        stream_end = StreamEnd(reason=reason)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(stream_end.model_dump_json())
            except RuntimeError:
                pass  # WebSocket disconnected during send
    
    async def _send_error(self, error_code: str, message: str) -> None:
        error = ErrorMessage(error_code=error_code, message=message)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(error.model_dump_json())
            except Exception as e:
                logger.error(f"Error sending error message: {e}")
    
    async def send_agent_input_request(
        self, request_id: str, prompt: str, agent_name: str, feedback_context: dict[str, Any] | None = None
    ) -> None:
        request = AgentInputRequest(
            request_id=request_id,
            prompt=prompt,
            agent_name=agent_name,
            feedback_context=feedback_context
        )

        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(request.model_dump_json())
            except RuntimeError:
                pass
    
    
    async def _handle_human_input_response(self, message_dict: dict) -> None:
        try:
            response = HumanInputResponse(**message_dict)
            success = self.agent_input_queue.provide_input(
                response.request_id,
                response.user_input
            )

            if not success:
                await self._send_error(
                    "INVALID_REQUEST_ID",
                    f"No pending input request found for ID: {response.request_id}"
                )

        except Exception as e:
            await self._send_error("HUMAN_INPUT_RESPONSE_ERROR", str(e))
    
    async def _cleanup(self) -> None:
        if self.agent_input_queue:
            self.agent_input_queue.cancel_all_pending()

        # Remove this WebSocket from the session
        if self.session:
            self.session.remove_websocket(self.websocket)

        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.close()

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any
import uuid

from autogen_agentchat.base import TaskResult
from autogen_core.tools import Tool

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

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocket, WebSocketState

from handlers.agent_input_queue import AgentInputQueue
from handlers.session_manager import get_session_manager, Session
from models import (
    HumanInputResponse,
    AgentInputRequest,
    AgentMessage,
    AgentTeamNames,
    AgentDetails,
    ErrorMessage,
    InterruptAcknowledged,
    MessageType,
    ParticipantNames,
    RunConfig,
    StateUpdate,
    StreamEnd,
    TreeUpdate,
    ToolCall,
    ToolCallInfo,
    ToolExecution,
    ToolExecutionResult,
    UserDirectedMessage,
    UserInterrupt
)
from utils.yaml_utils import get_agent_team_names, get_agent_details, get_team_main_tasks, get_summarization_system_prompt
from utils.summarization import init_summarizer, summarize_message

# we need to implement an autogen agent team factory
from handlers.state_manager import StateManager
from factory.team_factory import AgentTeamContext, init_team
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        print("✓ WebSocket accepted")

        try:
            # Step 1: Send available agent team names to frontend
            print("→ Sending agent team names...")
            team_names = get_agent_team_names()
            await self._send_agent_team_names(team_names)
            print("✓ Agent team names sent")

            await self._send_agent_details()

            # Step 2: Wait for config from frontend
            print("→ Waiting for config from frontend...")
            config_data = await self.websocket.receive_text()
            print(f"✓ Received config: {config_data[:100]}...")
            config_dict = json.loads(config_data)

            self.agent_team_config = RunConfig(**config_dict)

            # Get or create session based on session_id
            session_id = self.agent_team_config.session_id
            print(f"→ Creating session with ID: {session_id}")
            state_file = Path(os.getenv("STATE_FILE_PATH", f"agent_run_state_{session_id}.json"))

            self.session = self.session_manager.get_or_create_session(
                session_id=session_id,
                state_file_path=str(state_file)
            )
            print(f"✓ Session created/retrieved")

            # Register this WebSocket with the session
            self.session.add_websocket(self.websocket)
            print(f"✓ WebSocket registered with session")

            # Initialize the agent team if not already initialized for this session
            if self.session.agent_team_context is None:
                print("→ Initializing agent team...")
                await self._initialize_run()
                print("✓ Agent team initialized")

                # Send participant names to frontend for agent selection dropdown
                print("→ Sending participant names...")
                await self._send_participant_names()
                print("✓ Participant names sent")

                # Use provided initial_topic or default task from backend
                initial_topic = self.agent_team_config.initial_topic or get_team_main_tasks()

                # Format the initial_topic with config values if available
                if self.agent_team_config.company_name and self.agent_team_config.bill_name and self.agent_team_config.congress:
                    initial_topic = initial_topic.format(
                        company_name=self.agent_team_config.company_name,
                        bill_name=self.agent_team_config.bill_name,
                        bill=self.agent_team_config.bill_name,  # {bill} is same as {bill_name}
                        year=self.agent_team_config.congress,    # {year} maps to congress
                        congress=self.agent_team_config.congress
                    )

                print(f"→ Initializing root message with topic: {initial_topic[:100]}...")
                self.session.state_manager.initialize_root(
                    agent_name="You", message=initial_topic
                )
                print("✓ Root initialized")

                # Broadcast initial tree state to all connections in session
                print("→ Broadcasting tree update...")
                await self._broadcast_tree_update()
                print("✓ Tree broadcasted")

                # Step 3: Start the conversation stream
                print("→ Starting conversation stream...")
                await self._conversation_stream(initial_topic)
                print("✓ Conversation stream completed")
            else:
                # Send current state to this new connection
                await self._send_tree_update()
                # Note: Stream is already running in another connection, just observe


        except json.JSONDecodeError as e:
            print(f"✗ JSON Error: {str(e)}")
            await self._send_error("CONFIG_JSON_ERROR", f"Invalid JSON: {str(e)}")
        except ValueError as e:
            print(f"✗ Value Error: {str(e)}")
            await self._send_error("CONFIG_VALIDATION_ERROR", str(e))
        except WebSocketDisconnect as e:
            print(f"✗ WebSocket Disconnected")
            pass
        except Exception as e:
            print(f"✗ Handler Error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            await self._send_error("HANDLER_ERROR", str(e))


        finally:
            await self._cleanup()


    async def _initialize_run(self) -> None:

        if not self.session:
            raise RuntimeError("Session not initialized")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")

        # Get summarization system prompt from yaml
        summarization_prompt = get_summarization_system_prompt()

        # Initialize the summarizer with system prompt from yaml
        init_summarizer(api_key=api_key, model="gpt-4o-mini", system_prompt=summarization_prompt)

        # Initialize agent team and store in session (shared across all connections)
        self.session.agent_team_context = await init_team(
            api_key=api_key,
            agent_input_queue=self.agent_input_queue,
            company_name=self.agent_team_config.company_name,
            bill_name=self.agent_team_config.bill_name,
            congress=self.agent_team_config.congress
        )

        # Update StateManager with display_names from agent team context
        self.session.state_manager.display_names = self.session.agent_team_context.display_names

    async def _conversation_stream(self, initial_topic: str) -> None:

        if not self.session or not self.session.agent_team_context or not self.session.state_manager:
            raise RuntimeError("Session, agent team context or state manager not initialized")
        
        total_messages = 0

        # starting the stream here...
        stream = self.session.agent_team_context.team.run_stream(task=initial_topic)
        message_task = asyncio.create_task(stream.__anext__())
        client_task: asyncio.Task[str] | None = asyncio.create_task(
            self.websocket.receive_text()
        )

        try:

            while True:

                pending: set[asyncio.Task[object]] = {message_task}
                if client_task is not None:
                    pending.add(client_task)
                
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                if message_task in done: # there is a message to handle
                    try:
                        message = message_task.result()
                    except StopAsyncIteration:

                        # stream ended naturally
                        await self._send_stream_end("Run completed")

                        # Process any pending client messages before exiting
                        # (e.g., user might have clicked interrupt just as stream ended)
                        if client_task is not None and client_task.done():
                            await self._process_client_command(client_task)

                        break
                    except asyncio.CancelledError:
                        # Task was cancelled (rare - should mostly be handled by soft cancellation)
                        # Don't break the connection, just skip this message and continue
                        print("⚠️ Message task received CancelledError - continuing stream")
                        message_task = asyncio.create_task(stream.__anext__())
                        continue
                    except Exception as e:
                        # Catch any other exceptions to prevent connection breaks
                        print(f"⚠️ Stream error (non-fatal): {type(e).__name__}: {str(e)[:100]}")
                        # Try to continue the stream
                        message_task = asyncio.create_task(stream.__anext__())
                        continue

                    if isinstance(message, BaseChatMessage):
                        total_messages += 1
                        print(f"[{total_messages}] [{message.source}]: {message.content}")
                        await self._process_agent_message(message)
                    
                    elif isinstance(message, ToolCallRequestEvent):
                        print(f"[TOOL CALL] {message.source} is calling tools: {[tc.name for tc in message.content]}")
                        await self._send_tool_calls_request(message)

                    elif isinstance(message, ToolCallExecutionEvent):
                        print(f"[TOOL RESULTS] Tool execution completed for {message.source}")
                        await self._send_tool_calls_execution(message)

                    elif isinstance(message, StateUpdateEvent):
                        await self._send_state_update(message)

                    elif isinstance(message, SelectorEvent):
                        print(f"\n[{message.source}] 🎯 Selector: {message.content}")
                    
                    elif isinstance(message, UserInputRequestedEvent):
                        print(
                            f"\n💬 [{message.source}] is requesting input from the human user."
                        )
                    
                    elif hasattr(message, "stop_reason"):
                        print(f"🏁 Stream ended: {message.stop_reason}")
                        await self._send_stream_end(str(message.stop_reason))

                        # Process any pending client messages before exiting
                        if client_task is not None and client_task.done():
                            await self._process_client_command(client_task)

                        break
                    
                    elif isinstance(message, BaseAgentEvent):
                        # Skip printing ModelClientStreamingChunkEvent
                        if not isinstance(message, ModelClientStreamingChunkEvent):
                            print(
                                f"\n[{message.source}] {type(message).__name__}: {message.to_text()[:200]}"
                            )
                    
                    message_task = asyncio.create_task(stream.__anext__())
                
                # Handle a client message
                if client_task is not None and client_task in done:
                    client_task = await self._process_client_command(client_task)
                    if client_task is None: # if the client disconnected in the meantime
                        break
        
        except asyncio.CancelledError:
            raise
        finally:

            # Here we clean up the tasks
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
        
        # 3 things that can go wrong here:
        # 1. the task was cancelled
        # 2. the client disconnected
        # 3. some other exception occurred
        except asyncio.CancelledError:
            return None
        except (EOFError, WebSocketDisconnect):
            print("\nClient disconnected.")
            return None
        except Exception as exc:
            print(f"⚠️ Client message failed: {exc}")
            import traceback
            traceback.print_exc()
            return asyncio.create_task(self.websocket.receive_text())


        try:
            message_dict = json.loads(raw_message)
            message_type = message_dict.get("type")

            if message_type == MessageType.USER_INTERRUPT:
                await self._handle_interrupt(message_dict)
            elif message_type == MessageType.HUMAN_INPUT_RESPONSE:
                await self._handle_human_input_response(message_dict)
            elif message_type == MessageType.USER_DIRECTED_MESSAGE:
                await self._handle_user_message(message_dict)
        except json.JSONDecodeError as e:
            print(f"Failed to decode client message: {e}")
        except Exception as e:
            print(f"Error processing client message: {e}")
            await self._send_error("MESSAGE_PROCESSING_ERROR", str(e))
                    
        
        return asyncio.create_task(self.websocket.receive_text())
    
    async def _handle_interrupt(self, message_dict: dict[str, Any]) -> None:
        try:
            print("=" * 60)
            print("USER INTERRUPT RECEIVED FROM FRONTEND")
            print("=" * 60)

            interrupt_msg = UserInterrupt(**message_dict)

            if not self.session.agent_team_context:
                raise RuntimeError("Agent team context not initialized")

            # Interrupt the agent team conversation via UserControlAgent
            await self.session.agent_team_context.user_control.interrupt(self.session.agent_team_context.team)

            print("TEAM SUCCESSFULLY INTERRUPTED")
            print("=" * 60)

            await self._send_interrupt_acknowledged() # notify client that the backend has recieved and is processing the interrupt request

        except Exception as e:
            await self._send_error("INTERRUPT_ERROR", str(e))
        

    async def _handle_user_message(self, message_dict: dict[str, Any]) -> None:
        try:
            user_message = UserDirectedMessage(**message_dict)

            if not self.session.agent_team_context:
                await self._send_error(
                    "NO_AGENT_TEAM_CONTEXT",
                    "Agent team context not initialized",
                )
                return

            # Validate target agent exists
            if user_message.target_agent not in self.session.agent_team_context.participant_names:
                await self._send_error(
                    "INVALID_TARGET_AGENT",
                    f"Agent '{user_message.target_agent}' not found. "
                    f"Valid agents: {', '.join(self.session.agent_team_context.participant_names)}",
                )
                return
            print(
                f"Sending message to {user_message.target_agent} with trim_up={user_message.trim_count}"
            )

            user_node = self.session.state_manager.create_branch(
                trim_count=user_message.trim_count,
                user_message=user_message.content
            )

            self.session.state_manager.save_to_file()

            await self._send_tree_update()

            result: TaskResult = await self.session.agent_team_context.user_control.send( # calling UserControlAgent directly
                self.session.agent_team_context.team,
                user_message.content,
                user_message.target_agent,
                trim_up=user_message.trim_count,
            )

            if result and getattr(result, "messages", None):
                for response in result.messages:
                    if isinstance(
                        response,
                        (
                            TextMessage,
                            StopMessage,
                            ToolCallSummaryMessage,
                            HandoffMessage
                        )
                    ):
                        if hasattr(response, "content"):
                            print(f"[{response.source}]: {response.content}")
                            await self._process_agent_message(response)
        
        except Exception as e:

            print(f"Error handling the user message: {e}")

            await self._send_error("USER_MESSAGE_ERROR", str(e))

            with contextlib.suppress(Exception):
                await self.session.agent_team_context.team.resume() # just resume talking when there is an error with the User send message
    
    async def _process_agent_message(self, message: ChatMessage) -> None:

        if not self.session.state_manager:
            raise RuntimeError("State manager not initialized")

        agent_name = message.source if hasattr(message, "source") else "Unknown"
        content = str(message.content)

        # Generate summary for the message
        logger.info(f"Generating summary for message from {agent_name}")
        summary = await summarize_message(agent_name=agent_name, message_content=content)
        logger.info(f"Summary generated: {summary[:100]}...")

        # Create a new node for this message with summary
        node = self.session.state_manager.add_node(
            agent_name=agent_name,
            message=content,
            summary=summary
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
        self._pending_agent_messages.append(agent_msg)
        logger.info(
            "Queued agent message %s awaiting state update (%d pending)",
            node_id,
            len(self._pending_agent_messages)
        )
    
    async def _send_agent_team_names(self, team_names: list[str]) -> None:
        # Send available agent team configuration names to frontend
        team_names_msg = AgentTeamNames(agent_team_names=team_names)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(team_names_msg.model_dump_json())

    async def _send_agent_details(self) -> None:
        # Send agent details (names and descriptions) to frontend
        agents_data = get_agent_details()
        agent_details_msg = AgentDetails(agents=agents_data)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(agent_details_msg.model_dump_json())

    async def _send_participant_names(self) -> None:
        # Send individual agent participant names to frontend for agent selection dropdown
        if not self.session or not self.session.agent_team_context:
            raise RuntimeError("Agent team context not initialized")

        participant_names_msg = ParticipantNames(
            participant_names=self.session.agent_team_context.participant_names
        )
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(participant_names_msg.model_dump_json())

    async def _send_message(self, message: AgentMessage) -> None:
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(message.model_dump_json())

    async def _flush_pending_agent_messages(self) -> None:
        if not self._pending_agent_messages:
            return

        pending = self._pending_agent_messages.copy()
        self._pending_agent_messages.clear()
        logger.info("Flushing %d pending agent messages after state update", len(pending))

        for queued_message in pending:
            await self._send_message(queued_message)
            await self._send_tree_update()

    async def _send_tree_update(self) -> None:
        """Send tree update to this specific WebSocket connection only."""
        if not self.session.state_manager:
            raise RuntimeError("State manager not initialized")
        if self.session.state_manager.root is None:
            raise RuntimeError("State manager root node is None")
            return

        tree_update = TreeUpdate(
            root=self.session.state_manager.root,
            current_branch_id=self.session.state_manager.current_branch_id
        )

        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(tree_update.model_dump_json())
            except Exception as e:
                print(f"Error sending tree update: {e}")
                raise

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
            await self.websocket.send_text(ack.model_dump_json())

    async def _send_tool_calls_request(self, message: ToolCallRequestEvent) -> None:
        # Create new node for tool call
        node = self.session.state_manager.add_node(
            agent_name=message.source,
            message=message.to_text(),
            node_type="tool_call"
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
            await self.websocket.send_text(tc_request.model_dump_json())
    
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

        tc_execution = ToolExecution(
            agent_name=message.source,
            results=results,
            node_id=self.current_tool_call_node_id
        )
        await self._send_tree_update()

        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(tc_execution.model_dump_json())

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
                json_data = state_update.model_dump_json()
                await self.websocket.send_text(json_data)
            else:
                logger.warning(f"Cannot send STATE_UPDATE - WebSocket not connected")
        finally:
            await self._flush_pending_agent_messages()


    async def _send_stream_end(self, reason: str) -> None:
        await self._flush_pending_agent_messages()

        stream_end = StreamEnd(reason=reason)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(stream_end.model_dump_json())
    
    async def _send_error(self, error_code: str, message: str) -> None:
        error = ErrorMessage(error_code=error_code, message=message)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(error.model_dump_json())
            except Exception as e:
                print(f"Error sending error message: {e}")
    
    async def send_agent_input_request(
        self, request_id: str, prompt: str, agent_name: str
    ) -> None:
        
        request = AgentInputRequest(
            request_id=request_id,
            prompt=prompt,
            agent_name=agent_name
        )

        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(request.model_dump_json())
    
    
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
            else:
                print(f"Received human input response for request ID: {response.request_id}")
            
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

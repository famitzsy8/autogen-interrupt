"""WebSocket handler for research team communication with HierarchicalGroupChat."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from pathlib import Path
from typing import Any

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ChatMessage,
    CodeExecutionEvent,
    CodeGenerationEvent,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    SelectorEvent,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
    ToolCallSummaryMessage,
    UserInputRequestedEvent,
)
from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocket, WebSocketState

from agent_input_queue import AgentInputQueue
from models import (
    AgentInputRequest,
    AgentInputResponse,
    AgentMessage,
    ErrorMessage,
    InterruptAcknowledged,
    MessageType,
    StreamEnd,
    TreeUpdate,
    UserDirectedMessage,
    UserInterrupt,
)
from research_team import ResearchContext, build_research_team, get_initial_topic
from state_manager import StateManager


class WebSocketHandler:
    """Handles WebSocket connections for research team with HierarchicalGroupChat."""

    def __init__(self, websocket: WebSocket) -> None:
        """
        Initialize WebSocket handler.

        Args:
            websocket: FastAPI WebSocket connection
        """
        self.websocket = websocket
        self.state_manager: StateManager | None = None
        self.research_context: ResearchContext | None = None
        self.agent_input_queue = AgentInputQueue()
        self.agent_input_queue.websocket_handler = self
        self.streaming_chunks: list[str] = []  # Track streaming chunks

    async def handle_connection(self) -> None:
        """
        Main handler for WebSocket connection lifecycle.
        Adapted from dr_interrupt.py research_stream function.
        """
        print("=== WebSocket connection handler started ===")
        await self.websocket.accept()
        print("=== WebSocket connection accepted ===")

        try:
            # Initialize research team and state manager
            print("=== Initializing research team... ===")
            await self._initialize_research()
            print("=== Research team initialized ===")

            # Get initial topic
            initial_topic = get_initial_topic()

            # Initialize conversation tree with root node
            root_node = self.state_manager.initialize_root(
                agent_name="System", message=initial_topic
            )
            await self._send_tree_update()

            # Start the conversation stream
            print("🔬 Starting research stream...")
            await self._conversation_stream(initial_topic)

        except WebSocketDisconnect as e:
            print(f"=== WebSocket client disconnected: {e} ===")
        except Exception as e:
            print(f"=== Error in WebSocket handler: {e} ===")
            import traceback
            traceback.print_exc()
            await self._send_error("HANDLER_ERROR", str(e))
        finally:
            print("=== Cleaning up WebSocket connection ===")
            await self._cleanup()
            print("=== WebSocket handler finished ===")

    async def _initialize_research(self) -> None:
        """Initialize research team and state manager."""
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")

        # Build research team with agent input queue support
        self.research_context = build_research_team(
            api_key=api_key,
            max_messages=60,
            agent_input_queue=self.agent_input_queue,
        )

        # Initialize state manager
        state_file = Path(os.getenv("STATE_FILE_PATH", "research_state.json"))
        self.state_manager = StateManager(state_file)

    async def _conversation_stream(self, initial_topic: str) -> None:
        """
        Stream research messages while handling WebSocket client commands.
        Adapted from dr_interrupt.py research_stream function.
        """
        if not self.research_context or not self.state_manager:
            raise RuntimeError("Research context not initialized")

        total_messages = 0
        print("Available agents: " + " | ".join(self.research_context.participant_names))

        # Start the research stream
        stream = self.research_context.team.run_stream(task=initial_topic)
        message_task = asyncio.create_task(stream.__anext__())
        client_task: asyncio.Task[str] | None = asyncio.create_task(
            self.websocket.receive_text()
        )

        try:
            while True:
                # Wait for either a stream message or client message
                pending: set[asyncio.Task[object]] = {message_task}
                if client_task is not None:
                    pending.add(client_task)  # type: ignore[arg-type]

                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                # Handle stream message
                if message_task in done:
                    try:
                        message = message_task.result()
                    except StopAsyncIteration:
                        print("=== Stream ended naturally ===")
                        await self._send_stream_end("Research completed")
                        break

                    # Handle streaming chunks
                    if isinstance(message, ModelClientStreamingChunkEvent):
                        # Stream chunks directly to frontend (no newline)
                        await self._send_streaming_chunk(message.content)
                        self.streaming_chunks.append(message.content)
                        message_task = asyncio.create_task(stream.__anext__())
                        continue

                    # Finalize streaming output
                    if self.streaming_chunks:
                        self.streaming_chunks.clear()

                    # Process chat messages
                    if isinstance(message, BaseChatMessage):
                        total_messages += 1
                        print(f"[{total_messages}] [{message.source}]: {message.content}")
                        await self._process_agent_message(message)

                    # Handle tool calls
                    elif isinstance(message, ToolCallRequestEvent):
                        print(f"\n[{message.source}] 🔧 Tool calls:")
                        for tool_call in message.content:
                            print(f"  - {tool_call.name}({tool_call.arguments})")

                    # Handle tool execution results
                    elif isinstance(message, ToolCallExecutionEvent):
                        print(f"\n[{message.source}] ✓ Tool execution results")

                    # Handle code generation
                    elif isinstance(message, CodeGenerationEvent):
                        print(
                            f"\n[{message.source}] 💻 Generated code (attempt {message.retry_attempt + 1})"
                        )

                    # Handle code execution
                    elif isinstance(message, CodeExecutionEvent):
                        print(
                            f"\n[{message.source}] ▶️  Code execution (attempt {message.retry_attempt + 1})"
                        )

                    # Handle selector events
                    elif isinstance(message, SelectorEvent):
                        print(f"\n[{message.source}] 🎯 Selector: {message.content}")

                    # Handle UserProxyAgent input requests
                    elif isinstance(message, UserInputRequestedEvent):
                        print(
                            f"\n💬 [{message.source}] is requesting input from the human user."
                        )
                        # Input request is handled automatically by AgentInputQueue

                    # Check for stop reason
                    elif hasattr(message, "stop_reason"):
                        print(f"🏁 Stream ended: {message.stop_reason}")
                        await self._send_stream_end(str(message.stop_reason))
                        break

                    # Generic fallback for other events
                    elif isinstance(message, BaseAgentEvent):
                        print(
                            f"\n[{message.source}] {type(message).__name__}: {message.to_text()[:200]}"
                        )

                    # Create next message task
                    message_task = asyncio.create_task(stream.__anext__())

                # Handle client message
                if client_task is not None and client_task in done:
                    client_task = await self._process_client_command(client_task)
                    # If client disconnected, exit loop
                    if client_task is None:
                        break

        except asyncio.CancelledError:
            raise
        finally:
            # Clean up tasks
            for task in (message_task, client_task):
                if task is not None and not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

    async def _process_client_command(
        self, client_task: asyncio.Task[str]
    ) -> asyncio.Task[str] | None:
        """
        Handle completion of a client WebSocket message.
        Mirrors interrupt_cli.py:248-285 _process_command_task function.
        """
        try:
            raw_message = client_task.result()
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

        # Parse the message
        try:
            message_dict = json.loads(raw_message)
            message_type = message_dict.get("type")

            if message_type == MessageType.USER_INTERRUPT:
                await self._handle_interrupt(message_dict)
            elif message_type == MessageType.USER_DIRECTED_MESSAGE:
                await self._handle_user_message(message_dict)
            elif message_type == MessageType.AGENT_INPUT_RESPONSE:
                await self._handle_agent_input_response(message_dict)
            else:
                await self._send_error(
                    "INVALID_MESSAGE_TYPE", f"Unknown message type: {message_type}"
                )
        except json.JSONDecodeError as e:
            await self._send_error("JSON_PARSE_ERROR", str(e))
        except Exception as e:
            print(f"Error processing client message: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error("MESSAGE_PROCESSING_ERROR", str(e))

        # Return new client task to continue listening
        return asyncio.create_task(self.websocket.receive_text())

    async def _handle_interrupt(self, message_dict: dict[str, Any]) -> None:
        """
        Handle user interrupt request.
        Mirrors interrupt_cli.py _handle_interrupt function.
        """
        try:
            # Validate message
            UserInterrupt(**message_dict)

            if not self.research_context:
                raise RuntimeError("Research context not initialized")

            print("⏸️ Pausing conversation via UserControlAgent...")
            # Use UserControlAgent.interrupt
            await self.research_context.user_control.interrupt(self.research_context.team)
            print("=== Conversation interrupted successfully ===")

            # Send acknowledgment to client
            await self._send_interrupt_acknowledged()

        except Exception as e:
            print(f"⚠️ Failed to pause the conversation: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error("INTERRUPT_ERROR", str(e))

    async def _handle_user_message(self, message_dict: dict[str, Any]) -> None:
        """
        Handle user-directed message with optional branching.
        Mirrors interrupt_cli.py _handle_interrupt function (continued).
        """
        if not self.research_context or not self.state_manager:
            raise RuntimeError("Research context not initialized")

        try:
            # Validate and parse message
            user_msg = UserDirectedMessage(**message_dict)

            # Validate target agent exists
            if user_msg.target_agent not in self.research_context.participant_names:
                await self._send_error(
                    "INVALID_TARGET_AGENT",
                    f"Agent '{user_msg.target_agent}' not found. "
                    f"Valid agents: {', '.join(self.research_context.participant_names)}",
                )
                return

            print(
                f"📨 Sending message to {user_msg.target_agent} with trim_up={user_msg.trim_count}"
            )

            # Create branch in conversation tree
            user_node = self.state_manager.create_branch(
                trim_count=user_msg.trim_count,
                user_message=user_msg.content,
                user_name="User",
            )

            # Save state
            self.state_manager.save_to_file()

            # Send tree update showing the user's message
            await self._send_tree_update()

            # Use UserControlAgent.send to deliver message
            result: TaskResult = await self.research_context.user_control.send(
                self.research_context.team,
                user_msg.content,
                user_msg.target_agent,
                trim_up=user_msg.trim_count,
            )

            # Process responses from the result
            if result and getattr(result, "messages", None):
                print(f"📨 Processing {len(result.messages)} responses to user message")
                for response in result.messages:
                    if isinstance(
                        response,
                        (
                            TextMessage,
                            MultiModalMessage,
                            StopMessage,
                            ToolCallSummaryMessage,
                            HandoffMessage,
                        ),
                    ):
                        if hasattr(response, "content") and hasattr(response, "source"):
                            print(f"[{response.source}]: {response.content}")
                            await self._process_agent_message(response)

            # Note: The team automatically resumes after user_control.send()
            # The stream will continue naturally from where it left off

        except Exception as e:
            print(f"⚠️ Failed to deliver message: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error("USER_MESSAGE_ERROR", str(e))
            # Try to resume the team if it was interrupted
            with contextlib.suppress(Exception):
                await self.research_context.team.resume()

    async def _process_agent_message(self, message: ChatMessage) -> None:
        """
        Process an agent message and update state.

        Args:
            message: ChatMessage from autogen agent
        """
        if not self.state_manager:
            raise RuntimeError("State manager not initialized")

        # Extract agent name and content
        agent_name = message.source if hasattr(message, "source") else "Unknown"
        content = str(message.content)

        # Add node to conversation tree
        node = self.state_manager.add_node(agent_name=agent_name, message=content)

        # If node is None, it means this was a GroupChatManager message (just a counter increment)
        # Don't send message to client or tree update for these internal messages
        if node is None:
            return

        # Save state to file
        self.state_manager.save_to_file()

        # Send agent message to client
        agent_msg = AgentMessage(
            agent_name=agent_name, content=content, node_id=node.id
        )
        await self._send_message(agent_msg)

        # Send tree update
        await self._send_tree_update()

    async def _send_message(self, message: AgentMessage) -> None:
        """
        Send a message to the WebSocket client.

        Args:
            message: Message to send
        """
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(message.model_dump_json())

    async def _send_streaming_chunk(self, chunk: str) -> None:
        """
        Send a streaming chunk to the WebSocket client.

        Args:
            chunk: Streaming text chunk to send
        """
        if self.websocket.client_state == WebSocketState.CONNECTED:
            # TODO: Consider creating a StreamingChunk message type if frontend needs it
            # For now, just print to backend console as streaming happens on backend
            pass

    async def _send_tree_update(self) -> None:
        """Send tree update to client."""
        if not self.state_manager:
            raise RuntimeError("State manager not initialized")

        if self.state_manager.root is None:
            print("=== Tree update skipped: no root node ===")
            return

        tree_update = TreeUpdate(
            root=self.state_manager.root,
            current_branch_id=self.state_manager.current_branch_id,
        )

        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(tree_update.model_dump_json())
            except Exception as e:
                print(f"=== Failed to send tree update: {e} ===")
                raise

    async def _send_interrupt_acknowledged(self) -> None:
        """Send interrupt acknowledgment to client."""
        ack = InterruptAcknowledged()
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(ack.model_dump_json())

    async def _send_stream_end(self, reason: str) -> None:
        """
        Send stream end notification to client.

        Args:
            reason: Reason for stream termination
        """
        stream_end = StreamEnd(reason=reason)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(stream_end.model_dump_json())

    async def _send_error(self, error_code: str, message: str) -> None:
        """
        Send error message to client.

        Args:
            error_code: Error code identifier
            message: Human-readable error message
        """
        error = ErrorMessage(error_code=error_code, message=message)
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(error.model_dump_json())
            except Exception as e:
                print(f"Failed to send error message: {e}")

    async def send_agent_input_request(
        self, request_id: str, prompt: str, agent_name: str
    ) -> None:
        """
        Send agent input request to frontend.

        Called by AgentInputQueue when an agent (like UserProxyAgent) needs human input.

        Args:
            request_id: Unique identifier for this request
            prompt: The question/prompt for the human user
            agent_name: Name of the agent requesting input
        """
        request = AgentInputRequest(
            request_id=request_id,
            prompt=prompt,
            agent_name=agent_name
        )
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_text(request.model_dump_json())
            print(f"📨 Sent input request to frontend: {agent_name} - {request_id}")

    async def _handle_agent_input_response(self, message_dict: dict) -> None:
        """
        Handle human user's response to an agent input request.

        Called when frontend sends the user's answer to an AgentInputRequest.

        Args:
            message_dict: Raw message dictionary from client
        """
        try:
            response = AgentInputResponse(**message_dict)
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
                print(f"✓ Provided input for request: {response.request_id}")

        except Exception as e:
            print(f"⚠️ Failed to handle agent input response: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error("AGENT_INPUT_RESPONSE_ERROR", str(e))

    async def _cleanup(self) -> None:
        """Clean up resources on connection close."""
        # Cancel any pending agent input requests
        if self.agent_input_queue:
            self.agent_input_queue.cancel_all_pending()

        # Close WebSocket if still open
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.close()
            except Exception:
                pass

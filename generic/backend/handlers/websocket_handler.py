from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from autogen_agentchat.base import TaskResult
from generic.backend.models import AgentInputRequest, AgentMessage, AgentTeamNames, InterruptAcknowledged, StreamEnd, StreamingChunk, UserDirectedMessage, UserInterrupt

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

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocket, WebSocketState

from agent_input_queue import AgentInputQueue # not implemented yet
from models import (
    HumanInputResponse,
    AgentInputRequest,
    AgentMessage,
    AgentTeamNames,
    ErrorMessage,
    InterruptAcknowledged,
    MessageType,
    RunConfig,
    StreamEnd,
    StreamingChunk,
    TreeUpdate,
    UserDirectedMessage,
    UserInterrupt
)

# we need to implement an autogen agent team factory
from state_manager import StateManager 
from factory.team_factory import AgentTeamContext, init_team
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WebSocketHandler:

    # Handles the WebSocket connections for the agent team

    def __init__(self, websocket: WebSocket) -> None:

        self.websocket = websocket
        self.state_manager: StateManager | None = None
        # TODO: look at how "context" (ResearchContext in dr-backdend) fits into the YAML implementation
        self.agent_input_queue = self
        self.agent_input_queue.websocket_handler = self
        self.agent_team_context: AgentTeamContext | None = None
        self.agent_team_config = RunConfig | None = None
        self.current_streaming_agent: str | None = None
        self.current_streaming_node_id: str | None = None
    
    async def handle_connection(self) -> None:

        await self.websocket.accept()
        print("=== WebSocket connection has been accepted ===")

        try:

            config_data = await self.websocket.receive_text()
            config_dict = json.loads(config_data)

            self.agent_team_config = RunConfig(**config_dict)

            if self.research_config.selector_prompt:
                logger.debug(f"User selector prompt:\n{self.research_config.selector_prompt}")

            
            initial_topic = self.agent_team_config.initial_topic

            self.state_manager.initialize_root(
                agent_name="You", message=initial_topic
            )
            await self._send_tree_update()

            await self._conversation_stream(initial_topic)

        
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON parse error: {str(e)}")
            await self._send_error("CONFIG_JSON_ERROR", f"Invalid JSON: {str(e)}")
        except ValueError as e:
            logger.error(f"Config validation error: {str(e)}")
            await self._send_error("CONFIG_VALIDATION_ERROR", str(e))
        except WebSocketDisconnect as e:
            logger.warning(f"WebSocket client disconnected: {e}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {str(e)}", exc_info=True)
            await self._send_error("HANDLER_ERROR", str(e))


        finally:
            await self._cleanup()
            print("=== WebSocket handler finished ===")


    async def _initialize_run(self, selector_prompt: str | None = None) -> None:

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")
        
        # TODO: this is where we would build the research team based on the YAML file
        self.agent_team_context = await init_team(
            api_key=api_key,
            agent_input_queue=self.agent_input_queue,
            selector_prompt=selector_prompt
        )

        state_file = Path(os.getenv("STATE_FILE_PATH", "agent_run_state.json")) # TODO: make sure this file/directory exists and the env field exists
        self.state_manager = StateManager(state_file=state_file)
    
    async def _conversation_stream(self, initial_topic: str) -> None:

        if not self.agent_team_context or not self.state_manager:
            raise RuntimeError("Agent team context or state manager not initialized")
        
        total_messages = 0

        # starting the stream here...
        stream = self.agent_team_context.team.run_stream(task=initial_topic)
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
                        break
                    
                    if isinstance(message, ModelClientStreamingChunkEvent):
                        ...
                    
                    if self.streaming_chunks:
                        self.streaming_chunks.clear()
                    
                    if isinstance(message, BaseChatMessage):
                        ...
                    
                    elif isinstance(message, ToolCallRequestEvent):
                        ...
                    
                    elif isinstance(message, ToolCallExecutionEvent):
                        ...
                    
                    elif isinstance(message, SelectorEvent):
                        ...
                    
                    elif isinstance(message, UserInputRequestedEvent):
                        ...
                    
                    elif hasattr(message, "stop_reason"):
                        ...
                    
                    elif hasattr(message, BaseAgentEvent):
                        ...
                    
                    message_task = asyncio.create_task(stream.__anext__())
                
                # Handle a client message
                if client_task is not None and client_task in done:
                    client_task = await self._process_client_message(client_task)
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
                await self._handle_user_directed_message(message_dict)
            else:
                print(f"Unknown message type from client: {message_type}")
        except json.JSONDecodeError as e:
            print(f"Failed to decode client message: {e}")
        except Exception as e:
            print(f"Error processing client message: {e}")
            await self._send_error("MESSAGE_PROCESSING_ERROR", str(e))
                    
        
        return asyncio.create_task(self.websocket.receive_text())
    
    async def _handle_interrupt(self, message_dict: dict[str, Any]) -> None:
        try:

            UserInterrupt(**message_dict)

            if not self.agent_team_context:
                raise RuntimeError("Agent team context not initialized")

            print("Pausing conversation via UserControlAgent (WS handler)...")

            await self._send_interrupt_acknowledged() # notify client that the backend has recieved and is processing the interrupt request

        except Exception as e:
            await self._send_error("INTERRUPT_ERROR", str(e))
        

    async def _handle_user_message(self, message_dict: dict[str, Any]) -> None:
        try:

            user_message = UserDirectedMessage(**message_dict)

            if not self.agent_team_context:
                await self._send_error(
                    "INVALID_TARGET_AGENT",
                    f"Agent '{user_message.target_agent}' not found. "
                    f"Valid agents: {', '.join(self.research_context.participant_names)}",
                )
                return
            print(
                f"Sending message to {user_message.target_agent} with trim_up={user_message.trim_count}"
            )
        
            user_node = self.state_manager.create_branch(
                trim_count=user_message.trim_count,
                user_message=user_message.content,
                user_name="You" # TODO: check the codebase if the "You" labelling is consistent
            )

            self.state_manager.save_to_file()

            await self._send_tree_update()

            result: TaskResult = await self.agent_team_context.user_control.send( # calling UserControlAgent directly
                self.agent_team_context.team,
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
                await self.agent_team_context.team.resume() # just resume talking when there is an error with the User send message
    
    async def _process_agent_message(self, message: ChatMessage) -> None:
        ...
    
    async def _send_message(self, message: AgentMessage) -> None:
        ...
    
    async def _send_streaming_chunk(self, agent_name: str, chunk: str, node_id: str) -> None:
        ...
    
    async def _send_tree_update(self) -> None:
        ...

    async def _send_interrupt_acknowledged(self) -> None:
        ...
    
    async def _send_stream_end(self, reason: str) -> None:
        ...
    
    async def _send_error(self, error_code: str, message: str) -> None:
        ...
    
    async def _send_agent_input_request(
        self, request_id: str, prompt: str, agent_name: str
    ) -> None:
        ...
    
    async def _handle_agent_input_response(self, message_dict: dict) -> None:
        ...
    
    async def _cleanup(self) -> None:
        ...



"""Tests for WebSocket endpoint and handler."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from autogen_agentchat.messages import ChatMessage, TextMessage
from starlette.websockets import WebSocketState

from models import (
    MessageType,
    TreeNode,
    UserDirectedMessage,
    UserInterrupt,
)
from state_manager import StateManager
from websocket_handler import WebSocketHandler


@pytest.fixture
def temp_state_file(tmp_path: Path) -> Path:
    """Create a temporary state file for testing."""
    return tmp_path / "test_state.json"


@pytest.fixture
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock API key in environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")


@pytest.fixture
def mock_state_file(monkeypatch: pytest.MonkeyPatch, temp_state_file: Path) -> Path:
    """Set mock state file path in environment."""
    monkeypatch.setenv("STATE_FILE_PATH", str(temp_state_file))
    return temp_state_file


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket connection."""
    websocket = MagicMock()
    websocket.client_state = WebSocketState.CONNECTED
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


class TestWebSocketHandlerInitialization:
    """Tests for WebSocketHandler initialization."""

    def test_handler_initialization(self, mock_websocket: MagicMock) -> None:
        """Test WebSocketHandler initialization."""
        handler = WebSocketHandler(mock_websocket)

        assert handler.websocket == mock_websocket
        assert handler.state_manager is None
        assert handler.debate_context is None
        assert handler.is_streaming is False
        assert handler.interrupt_requested is False
        assert handler.stream_task is None


class TestWebSocketHandlerMessageSending:
    """Tests for message sending functionality."""

    @pytest.mark.asyncio
    async def test_send_tree_update(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test sending tree update to client."""
        handler = WebSocketHandler(mock_websocket)

        # Initialize state manager
        handler.state_manager = StateManager(mock_state_file)
        handler.state_manager.initialize_root("System", "Test message")

        # Send tree update
        await handler._send_tree_update()

        # Verify WebSocket send was called
        mock_websocket.send_text.assert_called_once()

        # Verify message structure
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.TREE_UPDATE
        assert "root" in message
        assert message["root"]["agent_name"] == "System"

    @pytest.mark.asyncio
    async def test_send_interrupt_acknowledged(
        self, mock_websocket: MagicMock
    ) -> None:
        """Test sending interrupt acknowledgment."""
        handler = WebSocketHandler(mock_websocket)

        await handler._send_interrupt_acknowledged()

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.INTERRUPT_ACKNOWLEDGED

    @pytest.mark.asyncio
    async def test_send_stream_end(self, mock_websocket: MagicMock) -> None:
        """Test sending stream end notification."""
        handler = WebSocketHandler(mock_websocket)

        await handler._send_stream_end("Test reason")

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.STREAM_END
        assert message["reason"] == "Test reason"

    @pytest.mark.asyncio
    async def test_send_error(self, mock_websocket: MagicMock) -> None:
        """Test sending error message."""
        handler = WebSocketHandler(mock_websocket)

        await handler._send_error("TEST_ERROR", "Test error message")

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.ERROR
        assert message["error_code"] == "TEST_ERROR"
        assert message["message"] == "Test error message"

    @pytest.mark.asyncio
    async def test_send_when_websocket_disconnected(
        self, mock_websocket: MagicMock
    ) -> None:
        """Test that messages are not sent when WebSocket is disconnected."""
        handler = WebSocketHandler(mock_websocket)
        mock_websocket.client_state = WebSocketState.DISCONNECTED

        await handler._send_error("TEST_ERROR", "Test message")

        # Should not attempt to send
        mock_websocket.send_text.assert_not_called()


class TestWebSocketHandlerInitializeDebate:
    """Tests for debate initialization."""

    @pytest.mark.asyncio
    async def test_initialize_debate_success(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test successful debate initialization."""
        handler = WebSocketHandler(mock_websocket)

        with patch("websocket_handler.build_debate") as mock_build:
            mock_context = MagicMock()
            mock_context.participant_names = ["Agent1", "Agent2"]
            mock_build.return_value = mock_context

            await handler._initialize_debate()

            assert handler.debate_context is not None
            assert handler.state_manager is not None
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_debate_missing_api_key(
        self, mock_websocket: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test initialization fails without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        handler = WebSocketHandler(mock_websocket)

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            await handler._initialize_debate()


class TestWebSocketHandlerProcessAgentMessage:
    """Tests for processing agent messages."""

    @pytest.mark.asyncio
    async def test_process_agent_message_creates_node(
        self, mock_websocket: MagicMock, mock_state_file: Path
    ) -> None:
        """Test that processing agent message creates tree node."""
        handler = WebSocketHandler(mock_websocket)
        handler.state_manager = StateManager(mock_state_file)
        handler.state_manager.initialize_root("System", "Initial message")

        # Create a chat message
        chat_message = TextMessage(source="Agent1", content="Test response")

        # Process the message
        await handler._process_agent_message(chat_message)

        # Verify node was added
        assert handler.state_manager.current_node is not None
        assert handler.state_manager.current_node.agent_name == "Agent1"
        assert handler.state_manager.current_node.message == "Test response"

        # Verify messages were sent (agent message + tree update)
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_process_agent_message_saves_state(
        self, mock_websocket: MagicMock, mock_state_file: Path
    ) -> None:
        """Test that processing agent message saves state to file."""
        handler = WebSocketHandler(mock_websocket)
        handler.state_manager = StateManager(mock_state_file)
        handler.state_manager.initialize_root("System", "Initial message")

        chat_message = TextMessage(source="Agent1", content="Test response")
        await handler._process_agent_message(chat_message)

        # Verify state file was created
        assert mock_state_file.exists()


class TestWebSocketHandlerInterrupt:
    """Tests for interrupt handling."""

    @pytest.mark.asyncio
    async def test_handle_interrupt_when_not_streaming(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test interrupt when not streaming sends immediate acknowledgment."""
        handler = WebSocketHandler(mock_websocket)
        handler.is_streaming = False

        interrupt_dict = {"type": MessageType.USER_INTERRUPT}
        await handler._handle_interrupt(interrupt_dict)

        # Should send interrupt acknowledged
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.INTERRUPT_ACKNOWLEDGED

    @pytest.mark.asyncio
    async def test_handle_interrupt_when_streaming(
        self, mock_websocket: MagicMock
    ) -> None:
        """Test interrupt when streaming sets flag."""
        handler = WebSocketHandler(mock_websocket)
        handler.is_streaming = True

        interrupt_dict = {"type": MessageType.USER_INTERRUPT}
        await handler._handle_interrupt(interrupt_dict)

        # Should set interrupt flag
        assert handler.interrupt_requested is True

        # Should not send message yet (will be sent when stream pauses)
        mock_websocket.send_text.assert_not_called()


class TestWebSocketHandlerUserMessage:
    """Tests for user-directed message handling."""

    @pytest.mark.asyncio
    async def test_handle_user_message_creates_branch(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test that user message creates a branch in the tree."""
        handler = WebSocketHandler(mock_websocket)

        # Initialize debate context
        with patch("websocket_handler.build_debate") as mock_build:
            mock_context = MagicMock()
            mock_context.participant_names = ["Agent1", "Agent2"]
            mock_build.return_value = mock_context
            await handler._initialize_debate()

        # Initialize tree
        handler.state_manager.initialize_root("System", "Initial")
        handler.state_manager.add_node("Agent1", "First response")

        # Handle user message
        user_msg_dict = {
            "type": MessageType.USER_DIRECTED_MESSAGE,
            "content": "My message",
            "target_agent": "Agent1",
            "trim_count": 0,
        }

        with patch.object(
            handler, "_resume_debate_with_user_message", new_callable=AsyncMock
        ):
            await handler._handle_user_message(user_msg_dict)

        # Verify branch was created with user message
        current_node = handler.state_manager.current_node
        assert current_node is not None
        assert current_node.agent_name == "User"
        assert current_node.message == "My message"

        # Verify tree update was sent
        assert mock_websocket.send_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_user_message_invalid_agent(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test error when targeting non-existent agent."""
        handler = WebSocketHandler(mock_websocket)

        # Initialize debate context
        with patch("websocket_handler.build_debate") as mock_build:
            mock_context = MagicMock()
            mock_context.participant_names = ["Agent1", "Agent2"]
            mock_build.return_value = mock_context
            await handler._initialize_debate()

        handler.state_manager.initialize_root("System", "Initial")

        # Handle user message with invalid agent
        user_msg_dict = {
            "type": MessageType.USER_DIRECTED_MESSAGE,
            "content": "My message",
            "target_agent": "InvalidAgent",
            "trim_count": 0,
        }

        await handler._handle_user_message(user_msg_dict)

        # Should send error
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.ERROR
        assert message["error_code"] == "INVALID_TARGET_AGENT"

    @pytest.mark.asyncio
    async def test_handle_user_message_with_trim(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test user message with trim_count."""
        handler = WebSocketHandler(mock_websocket)

        # Initialize debate context
        with patch("websocket_handler.build_debate") as mock_build:
            mock_context = MagicMock()
            mock_context.participant_names = ["Agent1"]
            mock_build.return_value = mock_context
            await handler._initialize_debate()

        # Create a tree with multiple nodes
        handler.state_manager.initialize_root("System", "Initial")
        handler.state_manager.add_node("Agent1", "Response 1")
        handler.state_manager.add_node("Agent1", "Response 2")

        # Handle user message with trim_count=1
        user_msg_dict = {
            "type": MessageType.USER_DIRECTED_MESSAGE,
            "content": "Branch from earlier",
            "target_agent": "Agent1",
            "trim_count": 1,
        }

        with patch.object(
            handler, "_resume_debate_with_user_message", new_callable=AsyncMock
        ):
            await handler._handle_user_message(user_msg_dict)

        # Verify branch point is correct (should be 1 step back)
        current_node = handler.state_manager.current_node
        assert current_node is not None
        assert current_node.agent_name == "User"


class TestWebSocketHandlerCleanup:
    """Tests for cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_cancels_stream_task(
        self, mock_websocket: MagicMock
    ) -> None:
        """Test that cleanup properly cancels running stream task."""
        handler = WebSocketHandler(mock_websocket)

        # Create a real asyncio task that we can cancel
        async def dummy_coroutine() -> None:
            await asyncio.sleep(100)

        handler.stream_task = asyncio.create_task(dummy_coroutine())

        # Call cleanup
        await handler._cleanup()

        # Task should be cancelled
        assert handler.stream_task.cancelled()

    @pytest.mark.asyncio
    async def test_cleanup_closes_websocket(self, mock_websocket: MagicMock) -> None:
        """Test that cleanup closes WebSocket connection."""
        handler = WebSocketHandler(mock_websocket)
        mock_websocket.client_state = WebSocketState.CONNECTED

        await handler._cleanup()

        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_already_closed_websocket(
        self, mock_websocket: MagicMock
    ) -> None:
        """Test that cleanup handles already closed WebSocket."""
        handler = WebSocketHandler(mock_websocket)
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        mock_websocket.close.side_effect = Exception("Already closed")

        # Should not raise exception
        await handler._cleanup()


class TestStateManagement:
    """Tests for state persistence during WebSocket session."""

    @pytest.mark.asyncio
    async def test_state_persists_to_file(
        self, mock_websocket: MagicMock, mock_state_file: Path
    ) -> None:
        """Test that conversation state is persisted to file."""
        handler = WebSocketHandler(mock_websocket)
        handler.state_manager = StateManager(mock_state_file)
        handler.state_manager.initialize_root("System", "Initial message")

        # Process a message
        chat_message = TextMessage(source="Agent1", content="Test message")
        await handler._process_agent_message(chat_message)

        # State file should exist and contain data
        assert mock_state_file.exists()

        # Load and verify state
        state_manager = StateManager(mock_state_file)
        state_manager.load_from_file()
        assert state_manager.root is not None
        assert len(state_manager.root.children) > 0
        assert state_manager.root.children[0].agent_name == "Agent1"


class TestUserInterruptValidation:
    """Tests for user interrupt validation."""

    @pytest.mark.asyncio
    async def test_interrupt_with_invalid_data(
        self, mock_websocket: MagicMock
    ) -> None:
        """Test interrupt with invalid data structure."""
        handler = WebSocketHandler(mock_websocket)
        handler.is_streaming = False

        # Invalid interrupt (wrong type value to cause validation error)
        invalid_dict = {"type": "invalid_type", "timestamp": "2025-01-01T00:00:00"}

        await handler._handle_interrupt(invalid_dict)

        # Should send error (validation will fail and trigger error handler)
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.ERROR


class TestUserMessageValidation:
    """Tests for user message validation."""

    @pytest.mark.asyncio
    async def test_user_message_with_empty_content(
        self, mock_websocket: MagicMock, mock_api_key: None, mock_state_file: Path
    ) -> None:
        """Test user message with empty content fails validation."""
        handler = WebSocketHandler(mock_websocket)

        with patch("websocket_handler.build_debate") as mock_build:
            mock_context = MagicMock()
            mock_context.participant_names = ["Agent1"]
            mock_build.return_value = mock_context
            await handler._initialize_debate()

        handler.state_manager.initialize_root("System", "Initial")

        # Invalid message (empty content)
        invalid_dict = {
            "type": MessageType.USER_DIRECTED_MESSAGE,
            "content": "",  # Empty
            "target_agent": "Agent1",
            "trim_count": 0,
        }

        await handler._handle_user_message(invalid_dict)

        # Should send error
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == MessageType.ERROR

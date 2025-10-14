"""Tests for Pydantic models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from models import (
    AgentMessage,
    ErrorMessage,
    InterruptAcknowledged,
    MessageType,
    StreamEnd,
    TreeNode,
    TreeUpdate,
    UserDirectedMessage,
    UserInterrupt,
)


class TestAgentMessage:
    """Tests for AgentMessage model."""

    def test_valid_agent_message(self) -> None:
        """Test creating a valid agent message."""
        msg = AgentMessage(
            agent_name="Jara_Supporter",
            content="I believe in social justice!",
            node_id="node_123",
        )

        assert msg.type == MessageType.AGENT_MESSAGE
        assert msg.agent_name == "Jara_Supporter"
        assert msg.content == "I believe in social justice!"
        assert msg.node_id == "node_123"
        assert isinstance(msg.timestamp, datetime)

    def test_agent_message_strips_whitespace(self) -> None:
        """Test that agent_name and content strip whitespace."""
        msg = AgentMessage(
            agent_name="  Jara_Supporter  ",
            content="Message content",
            node_id="node_123",
        )

        assert msg.agent_name == "Jara_Supporter"

    def test_agent_message_empty_name_fails(self) -> None:
        """Test that empty agent name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentMessage(
                agent_name="",
                content="Valid content",
                node_id="node_123",
            )

        errors = exc_info.value.errors()
        assert any("agent_name" in str(e) for e in errors)

    def test_agent_message_whitespace_only_name_fails(self) -> None:
        """Test that whitespace-only agent name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentMessage(
                agent_name="   ",
                content="Valid content",
                node_id="node_123",
            )

        errors = exc_info.value.errors()
        assert any("agent_name" in str(e) for e in errors)

    def test_agent_message_empty_content_fails(self) -> None:
        """Test that empty content raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentMessage(
                agent_name="Jara_Supporter",
                content="",
                node_id="node_123",
            )

        errors = exc_info.value.errors()
        assert any("content" in str(e) for e in errors)

    def test_agent_message_whitespace_only_content_fails(self) -> None:
        """Test that whitespace-only content raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AgentMessage(
                agent_name="Jara_Supporter",
                content="   ",
                node_id="node_123",
            )

        errors = exc_info.value.errors()
        assert any("content" in str(e) for e in errors)

    def test_agent_message_missing_fields_fails(self) -> None:
        """Test that missing required fields raises validation error."""
        with pytest.raises(ValidationError):
            AgentMessage(agent_name="Test")  # type: ignore[call-arg]


class TestUserInterrupt:
    """Tests for UserInterrupt model."""

    def test_valid_user_interrupt(self) -> None:
        """Test creating a valid user interrupt."""
        interrupt = UserInterrupt()

        assert interrupt.type == MessageType.USER_INTERRUPT
        assert isinstance(interrupt.timestamp, datetime)

    def test_user_interrupt_with_explicit_timestamp(self) -> None:
        """Test creating user interrupt with explicit timestamp."""
        now = datetime.now()
        interrupt = UserInterrupt(timestamp=now)

        assert interrupt.timestamp == now


class TestUserDirectedMessage:
    """Tests for UserDirectedMessage model."""

    def test_valid_user_directed_message_default_trim(self) -> None:
        """Test creating a valid user directed message with default trim_count."""
        msg = UserDirectedMessage(
            content="What about the economy?",
            target_agent="Neural_Agent",
        )

        assert msg.type == MessageType.USER_DIRECTED_MESSAGE
        assert msg.content == "What about the economy?"
        assert msg.target_agent == "Neural_Agent"
        assert msg.trim_count == 0
        assert isinstance(msg.timestamp, datetime)

    def test_valid_user_directed_message_with_trim(self) -> None:
        """Test creating user directed message with trim_count."""
        msg = UserDirectedMessage(
            content="Let me clarify",
            target_agent="Jara_Supporter",
            trim_count=3,
        )

        assert msg.trim_count == 3

    def test_user_directed_message_strips_whitespace(self) -> None:
        """Test that content and target_agent strip whitespace."""
        msg = UserDirectedMessage(
            content="Message content",
            target_agent="  Neural_Agent  ",
        )

        assert msg.target_agent == "Neural_Agent"

    def test_user_directed_message_empty_content_fails(self) -> None:
        """Test that empty content raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserDirectedMessage(
                content="",
                target_agent="Neural_Agent",
            )

        errors = exc_info.value.errors()
        assert any("content" in str(e) for e in errors)

    def test_user_directed_message_empty_target_fails(self) -> None:
        """Test that empty target_agent raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserDirectedMessage(
                content="Valid message",
                target_agent="",
            )

        errors = exc_info.value.errors()
        assert any("target_agent" in str(e) for e in errors)

    def test_user_directed_message_negative_trim_fails(self) -> None:
        """Test that negative trim_count raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserDirectedMessage(
                content="Valid message",
                target_agent="Neural_Agent",
                trim_count=-1,
            )

        errors = exc_info.value.errors()
        assert any("trim_count" in str(e) for e in errors)


class TestInterruptAcknowledged:
    """Tests for InterruptAcknowledged model."""

    def test_valid_interrupt_acknowledged(self) -> None:
        """Test creating a valid interrupt acknowledgment."""
        ack = InterruptAcknowledged()

        assert ack.type == MessageType.INTERRUPT_ACKNOWLEDGED
        assert ack.message == "Conversation interrupted. Ready for user input."
        assert isinstance(ack.timestamp, datetime)


class TestStreamEnd:
    """Tests for StreamEnd model."""

    def test_valid_stream_end(self) -> None:
        """Test creating a valid stream end message."""
        end = StreamEnd(reason="Max messages reached")

        assert end.type == MessageType.STREAM_END
        assert end.reason == "Max messages reached"
        assert isinstance(end.timestamp, datetime)


class TestErrorMessage:
    """Tests for ErrorMessage model."""

    def test_valid_error_message(self) -> None:
        """Test creating a valid error message."""
        error = ErrorMessage(
            error_code="NETWORK_ERROR",
            message="Failed to connect to backend",
        )

        assert error.type == MessageType.ERROR
        assert error.error_code == "NETWORK_ERROR"
        assert error.message == "Failed to connect to backend"
        assert isinstance(error.timestamp, datetime)


class TestTreeNode:
    """Tests for TreeNode model."""

    def test_valid_root_node(self) -> None:
        """Test creating a valid root tree node."""
        node = TreeNode(
            id="node_1",
            agent_name="Jara_Supporter",
            message="Initial message",
            parent=None,
            branch_id="main",
        )

        assert node.id == "node_1"
        assert node.agent_name == "Jara_Supporter"
        assert node.message == "Initial message"
        assert node.parent is None
        assert node.children == []
        assert node.is_active is True
        assert node.branch_id == "main"
        assert isinstance(node.timestamp, datetime)

    def test_valid_child_node(self) -> None:
        """Test creating a valid child node."""
        parent = TreeNode(
            id="node_1",
            agent_name="Jara_Supporter",
            message="Parent",
            parent=None,
            branch_id="main",
        )

        child = TreeNode(
            id="node_2",
            agent_name="Kast_Supporter",
            message="Child",
            parent="node_1",
            branch_id="main",
        )

        assert child.parent == "node_1"

    def test_tree_node_with_children(self) -> None:
        """Test tree node with children list."""
        child1 = TreeNode(
            id="node_2",
            agent_name="Agent1",
            message="Child 1",
            parent="node_1",
            branch_id="main",
        )

        child2 = TreeNode(
            id="node_3",
            agent_name="Agent2",
            message="Child 2",
            parent="node_1",
            branch_id="branch_2",
        )

        parent = TreeNode(
            id="node_1",
            agent_name="Agent0",
            message="Parent",
            parent=None,
            children=[child1, child2],
            branch_id="main",
        )

        assert len(parent.children) == 2
        assert parent.children[0].id == "node_2"
        assert parent.children[1].id == "node_3"

    def test_tree_node_inactive_branch(self) -> None:
        """Test tree node with is_active=False."""
        node = TreeNode(
            id="node_1",
            agent_name="Agent",
            message="Inactive",
            parent=None,
            is_active=False,
            branch_id="old_branch",
        )

        assert node.is_active is False

    def test_tree_node_empty_id_fails(self) -> None:
        """Test that empty ID raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TreeNode(
                id="",
                agent_name="Agent",
                message="Message",
                parent=None,
                branch_id="main",
            )

        errors = exc_info.value.errors()
        assert any("id" in str(e) for e in errors)

    def test_tree_node_empty_agent_name_fails(self) -> None:
        """Test that empty agent_name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TreeNode(
                id="node_1",
                agent_name="",
                message="Message",
                parent=None,
                branch_id="main",
            )

        errors = exc_info.value.errors()
        assert any("agent_name" in str(e) for e in errors)

    def test_tree_node_strips_whitespace(self) -> None:
        """Test that ID and agent_name strip whitespace."""
        node = TreeNode(
            id="  node_1  ",
            agent_name="  Agent  ",
            message="Message",
            parent=None,
            branch_id="main",
        )

        assert node.id == "node_1"
        assert node.agent_name == "Agent"


class TestTreeUpdate:
    """Tests for TreeUpdate model."""

    def test_valid_tree_update(self) -> None:
        """Test creating a valid tree update."""
        root = TreeNode(
            id="node_1",
            agent_name="Agent",
            message="Root",
            parent=None,
            branch_id="main",
        )

        update = TreeUpdate(
            root=root,
            current_branch_id="main",
        )

        assert update.type == MessageType.TREE_UPDATE
        assert update.root == root
        assert update.current_branch_id == "main"
        assert isinstance(update.timestamp, datetime)

    def test_tree_update_with_complex_tree(self) -> None:
        """Test tree update with nested tree structure."""
        child1 = TreeNode(
            id="node_2",
            agent_name="Agent1",
            message="Child 1",
            parent="node_1",
            branch_id="main",
        )

        child2 = TreeNode(
            id="node_3",
            agent_name="Agent2",
            message="Child 2",
            parent="node_1",
            branch_id="branch_2",
        )

        root = TreeNode(
            id="node_1",
            agent_name="Agent0",
            message="Root",
            parent=None,
            children=[child1, child2],
            branch_id="main",
        )

        update = TreeUpdate(
            root=root,
            current_branch_id="branch_2",
        )

        assert len(update.root.children) == 2
        assert update.current_branch_id == "branch_2"

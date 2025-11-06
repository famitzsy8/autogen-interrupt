"""Test all Pydantic models for validation logic"""

import pytest
from datetime import datetime
from models import (
    AgentMessage,
    StreamingChunk,
    UserInterrupt,
    UserDirectedMessage,
    InterruptAcknowledged,
    StreamEnd,
    ErrorMessage,
    TreeNode,
    AgentInputRequest,
    HumanInputResponse,
    RunConfig,
    ToolCall,
    ToolCallInfo,
    ToolExecution,
    ToolExecutionResult,
    MessageType,
)


class TestAgentMessage:
    def test_valid_agent_message(self):
        msg = AgentMessage(
            agent_name="orchestrator",
            content="Test message",
            node_id="node_123"
        )
        assert msg.agent_name == "orchestrator"
        assert msg.content == "Test message"
        assert msg.node_id == "node_123"
        assert msg.type == MessageType.AGENT_MESSAGE

    def test_empty_agent_name_fails(self):
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            AgentMessage(agent_name="", content="Test", node_id="node_123")

    def test_empty_content_fails(self):
        with pytest.raises(ValueError, match="content cannot be empty"):
            AgentMessage(agent_name="test", content="", node_id="node_123")

    def test_whitespace_trimming(self):
        msg = AgentMessage(
            agent_name="  orchestrator  ",
            content="  Test  ",
            node_id="  node_123  "
        )
        assert msg.agent_name == "orchestrator"
        assert msg.content == "Test"
        assert msg.node_id == "node_123"

    def test_timestamp_auto_generated(self):
        msg = AgentMessage(
            agent_name="orchestrator",
            content="Test",
            node_id="node_123"
        )
        assert isinstance(msg.timestamp, datetime)


class TestStreamingChunk:
    def test_valid_streaming_chunk(self):
        chunk = StreamingChunk(
            agent_name="orchestrator",
            content="Partial text...",
            node_id="node_456"
        )
        assert chunk.agent_name == "orchestrator"
        assert chunk.content == "Partial text..."
        assert chunk.node_id == "node_456"
        assert chunk.type == MessageType.STREAMING_CHUNK

    def test_empty_content_allowed(self):
        """Streaming chunks can have empty content"""
        chunk = StreamingChunk(
            agent_name="orchestrator",
            content="",
            node_id="node_456"
        )
        assert chunk.content == ""

    def test_whitespace_content_preserved(self):
        """Whitespace in streaming chunks should be preserved"""
        chunk = StreamingChunk(
            agent_name="orchestrator",
            content="   ",
            node_id="node_456"
        )
        assert chunk.content == "   "


class TestUserInterrupt:
    def test_user_interrupt_creation(self):
        interrupt = UserInterrupt()
        assert interrupt.type == MessageType.USER_INTERRUPT
        assert isinstance(interrupt.timestamp, datetime)


class TestUserDirectedMessage:
    def test_valid_user_directed_message(self):
        msg = UserDirectedMessage(
            content="Ask the bill specialist",
            target_agent="bill_specialist",
            trim_count=2
        )
        assert msg.content == "Ask the bill specialist"
        assert msg.target_agent == "bill_specialist"
        assert msg.trim_count == 2
        assert msg.type == MessageType.USER_DIRECTED_MESSAGE

    def test_default_trim_count(self):
        msg = UserDirectedMessage(
            content="Test message",
            target_agent="orchestrator"
        )
        assert msg.trim_count == 0

    def test_negative_trim_count_fails(self):
        with pytest.raises(ValueError):
            UserDirectedMessage(
                content="Test",
                target_agent="orchestrator",
                trim_count=-1
            )

    def test_empty_content_fails(self):
        with pytest.raises(ValueError, match="content cannot be empty"):
            UserDirectedMessage(
                content="",
                target_agent="orchestrator"
            )

    def test_empty_target_agent_fails(self):
        with pytest.raises(ValueError, match="target_agent cannot be empty"):
            UserDirectedMessage(
                content="Test",
                target_agent=""
            )


class TestTreeNode:
    def test_tree_node_creation(self):
        node = TreeNode(
            id="node_1",
            agent_name="orchestrator",
            message="Root message",
            parent=None,
            branch_id="main"
        )
        assert node.id == "node_1"
        assert node.agent_name == "orchestrator"
        assert node.message == "Root message"
        assert node.parent is None
        assert node.is_active is True
        assert node.branch_id == "main"
        assert len(node.children) == 0

    def test_tree_node_with_children(self):
        child = TreeNode(
            id="node_2",
            agent_name="bill_specialist",
            message="Child message",
            parent="node_1",
            branch_id="main"
        )
        parent = TreeNode(
            id="node_1",
            agent_name="orchestrator",
            message="Parent message",
            parent=None,
            branch_id="main",
            children=[child]
        )
        assert len(parent.children) == 1
        assert parent.children[0].id == "node_2"

    def test_inactive_node(self):
        node = TreeNode(
            id="node_1",
            agent_name="orchestrator",
            message="Test",
            branch_id="main",
            is_active=False
        )
        assert node.is_active is False

    def test_empty_id_fails(self):
        with pytest.raises(ValueError, match="id cannot be empty"):
            TreeNode(
                id="",
                agent_name="orchestrator",
                message="Test",
                branch_id="main"
            )

    def test_empty_agent_name_fails(self):
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            TreeNode(
                id="node_1",
                agent_name="",
                message="Test",
                branch_id="main"
            )


class TestAgentInputRequest:
    def test_valid_input_request(self):
        request = AgentInputRequest(
            request_id="req_123",
            prompt="Please provide feedback",
            agent_name="User_proxy"
        )
        assert request.request_id == "req_123"
        assert request.prompt == "Please provide feedback"
        assert request.agent_name == "User_proxy"
        assert request.type == MessageType.AGENT_INPUT_REQUEST

    def test_empty_request_id_fails(self):
        with pytest.raises(ValueError, match="request_id cannot be empty"):
            AgentInputRequest(
                request_id="",
                prompt="Test",
                agent_name="User_proxy"
            )

    def test_empty_prompt_fails(self):
        with pytest.raises(ValueError, match="prompt cannot be empty"):
            AgentInputRequest(
                request_id="req_123",
                prompt="",
                agent_name="User_proxy"
            )


class TestHumanInputResponse:
    def test_valid_human_input_response(self):
        response = HumanInputResponse(
            request_id="req_123",
            user_input="I approve this"
        )
        assert response.request_id == "req_123"
        assert response.user_input == "I approve this"
        assert response.type == MessageType.HUMAN_INPUT_RESPONSE

    def test_empty_user_input_fails(self):
        with pytest.raises(ValueError, match="user_input cannot be empty"):
            HumanInputResponse(
                request_id="req_123",
                user_input=""
            )


class TestRunConfig:
    def test_valid_run_config(self):
        config = RunConfig(
            run_id="run_123",
            initial_topic="Investigate HR 1234",
            selector_prompt="Select the next agent"
        )
        assert config.run_id == "run_123"
        assert config.initial_topic == "Investigate HR 1234"
        assert config.selector_prompt == "Select the next agent"
        assert config.type == MessageType.RUN_CONFIG

    def test_run_config_without_selector_prompt(self):
        config = RunConfig(
            run_id="run_123",
            initial_topic="Investigate HR 1234"
        )
        assert config.selector_prompt is None

    def test_empty_initial_topic_fails(self):
        with pytest.raises(ValueError):
            RunConfig(
                run_id="run_123",
                initial_topic=""
            )


class TestToolCall:
    def test_valid_tool_call(self):
        tool_info = ToolCallInfo(
            id="call_1",
            name="getBillSummary",
            arguments='{"bill_id": "HR1234"}'
        )
        tool_call = ToolCall(
            agent_name="bill_specialist",
            tools=[tool_info],
            node_id="node_789"
        )
        assert tool_call.agent_name == "bill_specialist"
        assert len(tool_call.tools) == 1
        assert tool_call.tools[0].name == "getBillSummary"
        assert tool_call.node_id == "node_789"
        assert tool_call.type == MessageType.TOOL_CALL

    def test_multiple_tool_calls(self):
        tool1 = ToolCallInfo(id="c1", name="tool1", arguments="{}")
        tool2 = ToolCallInfo(id="c2", name="tool2", arguments="{}")
        tool_call = ToolCall(
            agent_name="orchestrator",
            tools=[tool1, tool2],
            node_id="node_1"
        )
        assert len(tool_call.tools) == 2


class TestToolExecution:
    def test_valid_tool_execution(self):
        result = ToolExecutionResult(
            tool_call_id="call_1",
            tool_name="getBillSummary",
            success=True,
            result="Bill summary data"
        )
        execution = ToolExecution(
            agent_name="bill_specialist",
            results=[result],
            node_id="node_789"
        )
        assert execution.agent_name == "bill_specialist"
        assert len(execution.results) == 1
        assert execution.results[0].success is True
        assert execution.type == MessageType.TOOL_EXECUTION

    def test_failed_tool_execution(self):
        result = ToolExecutionResult(
            tool_call_id="call_1",
            tool_name="getBillSummary",
            success=False,
            result="Error: Bill not found"
        )
        execution = ToolExecution(
            agent_name="bill_specialist",
            results=[result],
            node_id="node_789"
        )
        assert execution.results[0].success is False


class TestInterruptAcknowledged:
    def test_interrupt_acknowledged(self):
        ack = InterruptAcknowledged()
        assert ack.type == MessageType.INTERRUPT_ACKNOWLEDGED
        assert "interrupted" in ack.message.lower()
        assert isinstance(ack.timestamp, datetime)


class TestStreamEnd:
    def test_stream_end(self):
        end = StreamEnd(reason="Max turns reached")
        assert end.reason == "Max turns reached"
        assert end.type == MessageType.STREAM_END


class TestErrorMessage:
    def test_error_message(self):
        error = ErrorMessage(
            error_code="INVALID_CONFIG",
            message="Configuration validation failed"
        )
        assert error.error_code == "INVALID_CONFIG"
        assert error.message == "Configuration validation failed"
        assert error.type == MessageType.ERROR

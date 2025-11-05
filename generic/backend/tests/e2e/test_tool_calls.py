"""
End-to-end tests for agent tool calls via MCP server.

These tests verify that agents can successfully:
1. Connect to the MCP server
2. List available tools
3. Execute tool calls with correct arguments
4. Handle tool responses
"""

import pytest
import os

from factory.team_factory import init_team
from handlers.agent_input_queue import AgentInputQueue
from handlers.state_manager import StateManager
from autogen_agentchat.messages import ToolCallRequestEvent, ToolCallExecutionEvent


@pytest.fixture
def api_key():
    """Get API key from environment"""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return key


@pytest.fixture

def state_file(tmp_path):
    """Create temporary state file"""
    return tmp_path / "test_tool_state.json"


class TestMCPToolCalls:
    """Test MCP tool call functionality"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_mcp_server_connection(self, api_key, state_file):
        """Test that agents can connect to MCP server"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)  # Initialize but not used directly

        # Initialize team - this should connect to MCP server
        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=3
        )

        # Verify team was initialized
        assert context.team is not None
        assert len(context.participant_names) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_simple_tool_call(self, api_key, state_file):
        """Test a simple tool call to convert lobby view bill ID"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=10
        )

        # Send a task that requires tool call
        task = "Use the convertLVtoCongress tool to convert the bill ID 's3688-116' to congress format."

        stream = context.team.run_stream(task=task)

        tool_call_found = False
        tool_result_found = False

        async for event in stream:
            # Check if tool call was made
            if isinstance(event, ToolCallRequestEvent):
                tool_call_found = True
                # Verify the tool call contains expected data
                for call in event.content:
                    if hasattr(call, 'name') and call.name == 'convertLVtoCongress':
                        assert 's3688-116' in str(call.arguments).lower()

            # Check if tool result was received
            if isinstance(event, ToolCallExecutionEvent):
                tool_result_found = True

        # At least one of these should be true for a successful tool call
        assert tool_call_found or tool_result_found, "No tool calls or results detected"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bill_sponsors_tool_call(self, api_key, state_file):
        """Test getBillSponsors tool call"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=10
        )

        # Task that requires getting bill sponsors
        task = """Get the sponsors of bill HR 1 from the 118th Congress using the getBillSponsors tool.
        The congress_index should be: {"congress": 118, "bill_type": "hr", "bill_number": 1}"""

        stream = context.team.run_stream(task=task)

        tool_call_found = False
        sponsor_data_found = False

        async for event in stream:
            if isinstance(event, ToolCallRequestEvent):
                for call in event.content:
                    if hasattr(call, 'name') and call.name == 'getBillSponsors':
                        tool_call_found = True

            if isinstance(event, ToolCallExecutionEvent):
                for result in event.content:
                    result_str = str(result.content).lower()
                    # Check if response contains sponsor information
                    if 'sponsor' in result_str or 'bioguide' in result_str:
                        sponsor_data_found = True

        assert tool_call_found, "getBillSponsors tool was not called"
        assert sponsor_data_found, "Sponsor data was not found in results"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_multiple_tool_calls_sequence(self, api_key, state_file):
        """Test multiple tool calls in sequence"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=20
        )

        # Task requiring multiple tool calls
        task = """For bill HR 1 from the 118th Congress:
        1. First get the sponsors
        2. Then get the cosponsors
        Use the appropriate tools."""

        stream = context.team.run_stream(task=task)

        tools_called = set()

        async for event in stream:
            if isinstance(event, ToolCallRequestEvent):
                for call in event.content:
                    if hasattr(call, 'name'):
                        tools_called.add(call.name)

        # Should have called at least one of the tools
        expected_tools = {'getBillSponsors', 'getBillCosponsors'}
        assert len(tools_called.intersection(expected_tools)) > 0, \
            f"Expected tools {expected_tools} but got {tools_called}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_tool_call_with_complex_arguments(self, api_key, state_file):
        """Test tool calls with complex nested arguments"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=10
        )

        task = """Get the summary of bill S 1 from the 117th Congress.
        Use congress_index: {"congress": 117, "bill_type": "s", "bill_number": 1}"""

        stream = context.team.run_stream(task=task)

        correct_arguments = False

        async for event in stream:
            if isinstance(event, ToolCallRequestEvent):
                for call in event.content:
                    if hasattr(call, 'name') and call.name == 'getBillSummary':
                        args_str = str(call.arguments).lower()
                        # Verify all required fields present
                        if 'congress' in args_str and 'bill_type' in args_str and 'bill_number' in args_str:
                            correct_arguments = True

        assert correct_arguments, "Tool call did not contain correct complex arguments"


class TestToolCallErrorHandling:
    """Test error handling in tool calls"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_invalid_tool_arguments(self, api_key, state_file):
        """Test handling of invalid tool arguments"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=10
        )

        # Task with intentionally invalid data
        task = """Try to get sponsors for a bill that doesn't exist: bill number 99999 from congress 999.
        Use the getBillSponsors tool."""

        stream = context.team.run_stream(task=task)

        # Should complete without crashing
        event_count = 0
        async for _ in stream:
            event_count += 1

        assert event_count > 0, "Stream should produce events even with invalid arguments"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_tool_call_recovery(self, api_key, state_file):
        """Test that agents can recover from failed tool calls"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=15
        )

        task = """First try an invalid bill ID 'xyz-999', then try a valid one 's1-117'."""

        stream = context.team.run_stream(task=task)

        tool_calls = 0
        async for event in stream:
            if isinstance(event, ToolCallRequestEvent):
                tool_calls += 1

        # Should have attempted multiple tool calls (trying to recover)
        assert tool_calls >= 1, "Should have attempted tool calls"


class TestToolCallStateTracking:
    """Test that tool calls are properly tracked in state"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_tool_call_events_in_stream(self, api_key, state_file):
        """Test that tool call events appear in stream"""
        input_queue = AgentInputQueue()
        _state_manager = StateManager(state_file)

        context = await init_team(
            api_key=api_key,
            agent_input_queue=input_queue,
            max_messages=10
        )

        task = "Convert bill ID 'hr1234-118' to congress format."

        stream = context.team.run_stream(task=task)

        event_types = []
        async for event in stream:
            event_types.append(type(event).__name__)

        # Should have various event types including tool-related ones
        assert len(event_types) > 0, "Should have events in stream"

        # Check if we got tool-related events
        has_tool_events = any('Tool' in et for et in event_types)
        assert has_tool_events, f"Expected tool events but got: {event_types}"

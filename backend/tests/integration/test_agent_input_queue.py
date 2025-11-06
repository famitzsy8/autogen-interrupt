"""Test AgentInputQueue functionality"""

import pytest
import asyncio
from handlers.agent_input_queue import AgentInputQueue


class TestAgentInputQueue:
    @pytest.mark.asyncio
    async def test_provide_input_before_request(self):
        """Providing input for non-existent request should fail"""
        queue = AgentInputQueue()
        success = queue.provide_input("fake_id", "some input")
        assert success is False

    def test_pending_request_tracking(self):
        """Test pending request count tracking"""
        queue = AgentInputQueue()
        assert queue.get_pending_count() == 0
        assert not queue.has_pending_requests()

    def test_cancel_all_pending(self):
        """Test cancelling all pending requests"""
        queue = AgentInputQueue()
        # This should not raise even with no pending requests
        queue.cancel_all_pending()
        assert queue.get_pending_count() == 0

    def test_initial_websocket_handler_none(self):
        """WebSocket handler should initially be None"""
        queue = AgentInputQueue()
        assert queue.websocket_handler is None

    def test_pending_requests_initially_empty(self):
        """Pending requests should start empty"""
        queue = AgentInputQueue()
        assert len(queue.pending_requests) == 0
        assert queue.get_pending_count() == 0


class TestAgentInputQueueWithMockHandler:
    @pytest.fixture
    def queue_with_mock_handler(self):
        """Create queue with a mock WebSocket handler"""
        queue = AgentInputQueue()

        class MockWebSocketHandler:
            def __init__(self):
                self.sent_requests = []

            async def send_agent_input_request(self, request_id: str, prompt: str, agent_name: str):
                self.sent_requests.append({
                    "request_id": request_id,
                    "prompt": prompt,
                    "agent_name": agent_name
                })

        queue.websocket_handler = MockWebSocketHandler()
        return queue

    @pytest.mark.asyncio
    async def test_get_input_sends_request(self, queue_with_mock_handler):
        """Getting input should send request via WebSocket handler"""
        queue = queue_with_mock_handler

        # Create a task that will request input
        async def request_input():
            return await queue.get_input(
                prompt="Please approve",
                agent_name="User_proxy"
            )

        # Start the request
        task = asyncio.create_task(request_input())

        # Give it time to send the request
        await asyncio.sleep(0.1)

        # Check that request was sent
        assert len(queue.websocket_handler.sent_requests) == 1
        sent = queue.websocket_handler.sent_requests[0]
        assert sent["prompt"] == "Please approve"
        assert sent["agent_name"] == "User_proxy"

        # Provide input to complete the task
        request_id = sent["request_id"]
        success = queue.provide_input(request_id, "Approved")
        assert success is True

        # Task should complete
        result = await task
        assert result == "Approved"

    @pytest.mark.asyncio
    async def test_get_input_without_handler_raises_error(self):
        """Getting input without handler should raise error"""
        queue = AgentInputQueue()

        with pytest.raises(RuntimeError, match="WebSocketHandler is not set"):
            await queue.get_input(
                prompt="Test",
                agent_name="User_proxy"
            )

    @pytest.mark.asyncio
    async def test_multiple_pending_requests(self, queue_with_mock_handler):
        """Should handle multiple pending requests"""
        queue = queue_with_mock_handler

        # Create two requests
        task1 = asyncio.create_task(queue.get_input("Prompt 1", "Agent1"))
        task2 = asyncio.create_task(queue.get_input("Prompt 2", "Agent2"))

        await asyncio.sleep(0.1)

        # Should have two pending requests
        assert queue.get_pending_count() == 2
        assert queue.has_pending_requests()

        # Provide inputs
        req1_id = queue.websocket_handler.sent_requests[0]["request_id"]
        req2_id = queue.websocket_handler.sent_requests[1]["request_id"]

        queue.provide_input(req1_id, "Response 1")
        queue.provide_input(req2_id, "Response 2")

        # Tasks should complete
        result1 = await task1
        result2 = await task2

        assert result1 == "Response 1"
        assert result2 == "Response 2"
        assert queue.get_pending_count() == 0

    @pytest.mark.asyncio
    async def test_cancel_pending_requests(self, queue_with_mock_handler):
        """Should be able to cancel pending requests"""
        queue = queue_with_mock_handler

        # Create a request
        task = asyncio.create_task(queue.get_input("Prompt", "Agent"))
        await asyncio.sleep(0.1)

        assert queue.get_pending_count() == 1

        # Cancel all pending
        queue.cancel_all_pending()

        # Task should be cancelled
        with pytest.raises(asyncio.CancelledError):
            await task

        assert queue.get_pending_count() == 0

    @pytest.mark.asyncio
    async def test_provide_input_for_completed_future(self, queue_with_mock_handler):
        """Providing input for already-completed future should fail gracefully"""
        queue = queue_with_mock_handler

        # Create and immediately complete a request
        task = asyncio.create_task(queue.get_input("Prompt", "Agent"))
        await asyncio.sleep(0.1)

        req_id = queue.websocket_handler.sent_requests[0]["request_id"]

        # Complete it once
        success1 = queue.provide_input(req_id, "Response")
        assert success1 is True

        result = await task
        assert result == "Response"

        # Try to provide input again for the same request
        success2 = queue.provide_input(req_id, "Another response")
        assert success2 is False

    @pytest.mark.asyncio
    async def test_request_creates_unique_ids(self, queue_with_mock_handler):
        """Each request should get a unique ID"""
        queue = queue_with_mock_handler

        task1 = asyncio.create_task(queue.get_input("Prompt 1", "Agent"))
        task2 = asyncio.create_task(queue.get_input("Prompt 2", "Agent"))

        await asyncio.sleep(0.1)

        req1_id = queue.websocket_handler.sent_requests[0]["request_id"]
        req2_id = queue.websocket_handler.sent_requests[1]["request_id"]

        assert req1_id != req2_id

        # Cleanup
        queue.cancel_all_pending()

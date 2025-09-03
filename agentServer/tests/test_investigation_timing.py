#!/usr/bin/env python3
"""
Timing test investigation to debug the specific timing issues with message box display.
This focuses on the exact scenario from the user's logs.
"""

import asyncio
import time
import json
from stream_accumulator import StreamAccumulator

class MockMessage:
    """Mock message object to simulate exact AutoGen messages from logs"""
    def __init__(self, message_type, source, content):
        self.__class__.__name__ = message_type
        self.source = source
        self.content = content
        
    def __getattr__(self, name):
        return getattr(self, name, None)

class TimingWebSocketCallback:
    """WebSocket callback that measures timing between events"""
    def __init__(self):
        self.events = []
        self.last_event_time = None
        
    async def __call__(self, event):
        now = time.time()
        if self.last_event_time:
            delay = now - self.last_event_time
            print(f"⏰ Delay since last event: {delay:.3f}s")
        
        self.events.append({**event, 'received_at': now})
        
        event_type = event['type']
        agent = event.get('data', {}).get('agent', 'unknown')
        simplified = event.get('data', {}).get('simplified', 'No summary')
        
        print(f"📡 [{time.strftime('%H:%M:%S', time.localtime(now))}] {event_type} from {agent}")
        print(f"   Summary: {simplified}")
        
        self.last_event_time = now

async def run_timing_test():
    """Test the exact timing scenario where boxes disappear"""
    print("⏰ Starting Timing Test Investigation")
    print("=" * 60)
    print("This simulates the exact pattern from user logs where committee_specialist")
    print("sends tokens but boxes don't appear until TERMINATE.")
    print()
    
    # Set up accumulator
    callback = TimingWebSocketCallback()
    accumulator = StreamAccumulator(
        websocket_callback=callback,
        allowed_agents=['orchestrator', 'committee_specialist', 'bill_specialist', 'actions_specialist', 'amendment_specialist', 'congress_member_specialist']
    )
    
    # Simulate the exact token sequence from user logs
    committee_tokens = [
        ' this', ' investigation', ' can', ' proceed', ' in', ' detail', '.\n\n', 'TER', 'MIN', 'ATE'
    ]
    
    print("🎯 Phase 1: Orchestrator sets up investigation")
    orchestrator_tokens = [
        "I will coordinate this investigation. ",
        "Let me delegate to the specialists. ",
        "Please await specialist reports."
    ]
    
    for token in orchestrator_tokens:
        mock_msg = MockMessage("ModelClientStreamingChunkEvent", "orchestrator", token)
        await accumulator.process_stream_message(mock_msg)
        await asyncio.sleep(0.01)  # Fast tokens
    
    # Wait for orchestrator finalization
    print("\n⏳ Waiting for orchestrator message finalization...")
    await asyncio.sleep(0.7)  # Should trigger finalization
    
    print("\n🎯 Phase 2: Committee specialist responds (problematic phase)")
    print("Simulating exact token sequence from logs...")
    
    # Track timing for each token
    token_start_time = time.time()
    
    for i, token in enumerate(committee_tokens):
        elapsed = time.time() - token_start_time
        print(f"Token {i+1:2d}/10: '{token:12}' at +{elapsed:.3f}s")
        
        mock_msg = MockMessage("ModelClientStreamingChunkEvent", "committee_specialist", token)
        await accumulator.process_stream_message(mock_msg)
        
        # Simulate the exact timing from logs (3-5ms between tokens)
        await asyncio.sleep(0.004)
    
    print(f"\n⏳ All tokens sent in {time.time() - token_start_time:.3f}s")
    print("Now waiting for finalization timeout...")
    
    # Wait for message finalization
    await asyncio.sleep(1.0)  # Should definitely trigger finalization
    
    print("\n🎯 Phase 3: Final cleanup")
    await accumulator.finish()
    
    print("\n📊 Timing Analysis:")
    print("=" * 60)
    
    if len(callback.events) >= 2:
        orchestrator_time = callback.events[0]['received_at']
        committee_time = callback.events[1]['received_at'] if len(callback.events) > 1 else None
        
        if committee_time:
            delay = committee_time - orchestrator_time
            print(f"Time between orchestrator and committee messages: {delay:.3f}s")
            
            if delay > 2.0:
                print("⚠️  ISSUE: Long delay suggests finalization timeout problem")
            elif delay < 0.1:
                print("⚠️  ISSUE: Very short delay suggests no finalization occurred")
            else:
                print("✅ Normal timing between messages")
    
    print(f"\nTotal events: {len(callback.events)}")
    for i, event in enumerate(callback.events):
        timestamp = time.strftime('%H:%M:%S.%f', time.localtime(event['received_at']))[:-3]
        agent = event.get('data', {}).get('agent', 'unknown')
        simplified = event.get('data', {}).get('simplified', 'No summary')[:50]
        print(f"  {i+1}. [{timestamp}] {agent:20} | {simplified}")

async def test_agent_filtering():
    """Test if non-allowed agents are being filtered out"""
    print("\n🔍 Testing Agent Filtering")
    print("=" * 40)
    
    callback = TimingWebSocketCallback()
    
    # Test with limited agents (original problem)
    print("Testing with limited agents (orchestrator, committee_specialist only):")
    accumulator_limited = StreamAccumulator(
        websocket_callback=callback,
        allowed_agents=['orchestrator', 'committee_specialist']
    )
    
    # Try sending message from bill_specialist
    mock_msg = MockMessage("ModelClientStreamingChunkEvent", "bill_specialist", "I am the bill specialist.")
    await accumulator_limited.process_stream_message(mock_msg)
    await asyncio.sleep(0.7)
    
    events_before = len(callback.events)
    print(f"Events with limited agents: {events_before}")
    
    # Test with all agents
    print("\nTesting with all agents:")
    callback.events.clear()
    accumulator_full = StreamAccumulator(
        websocket_callback=callback,
        allowed_agents=['orchestrator', 'committee_specialist', 'bill_specialist', 'actions_specialist', 'amendment_specialist', 'congress_member_specialist']
    )
    
    # Try same message
    mock_msg = MockMessage("ModelClientStreamingChunkEvent", "bill_specialist", "I am the bill specialist.")
    await accumulator_full.process_stream_message(mock_msg)
    await asyncio.sleep(0.7)
    
    events_after = len(callback.events)
    print(f"Events with all agents: {events_after}")
    
    if events_after > events_before:
        print("✅ Agent filtering was the issue!")
    else:
        print("⚠️  Agent filtering is not the main issue")

async def main():
    await run_timing_test()
    await test_agent_filtering()

if __name__ == "__main__":
    asyncio.run(main())
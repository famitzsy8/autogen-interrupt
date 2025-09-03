#!/usr/bin/env python3
"""
Simple test investigation to debug message box display issues.
This creates a controlled sequence of agent communications to test the frontend.
"""

import asyncio
import time
import json
from stream_accumulator import StreamAccumulator

class MockMessage:
    """Mock message object to simulate AutoGen messages"""
    def __init__(self, message_type, source, content):
        self.__class__.__name__ = message_type
        self.source = source
        self.content = content
        # Add realistic fields based on actual log format
        self.id = f'mock-{hash(f"{source}-{content}")}'
        self.models_usage = None
        self.metadata = {}
        self.created_at = None
        self.full_message_id = f'full-{hash(f"{source}-{content}")}'
        self.type = message_type
        
    def __getattr__(self, name):
        return getattr(self, name, None)

class MockWebSocketCallback:
    """Mock WebSocket callback to capture events"""
    def __init__(self):
        self.events = []
        
    async def __call__(self, event):
        self.events.append(event)
        print(f"📡 WebSocket Event: {event['type']} - {event.get('data', {}).get('agent', 'unknown')}")
        if 'data' in event and 'simplified' in event['data']:
            print(f"   Summary: {event['data']['simplified']}")

async def run_simple_test():
    """Run a simple test with orchestrator -> bill_specialist -> committee_specialist"""
    print("🧪 Starting Simple Test Investigation")
    print("=" * 50)
    
    # Set up accumulator with all agents
    callback = MockWebSocketCallback()
    accumulator = StreamAccumulator(
        websocket_callback=callback,
        allowed_agents=['orchestrator', 'bill_specialist', 'committee_specialist', 'actions_specialist', 'amendment_specialist', 'congress_member_specialist']
    )
    
    # Test sequence: Orchestrator delegation
    test_messages = [
        # 1. Orchestrator starts
        ("ModelClientStreamingChunkEvent", "orchestrator", "I will coordinate this investigation of "),
        ("ModelClientStreamingChunkEvent", "orchestrator", "the lobbying activities. "),
        ("ModelClientStreamingChunkEvent", "orchestrator", "Let me start by delegating tasks to specialists."),
        
        # 2. Bill specialist responds (this is where boxes might disappear)
        ("ModelClientStreamingChunkEvent", "bill_specialist", "I am the bill specialist. "),
        ("ModelClientStreamingChunkEvent", "bill_specialist", "I will retrieve information about the bill "),
        ("ModelClientStreamingChunkEvent", "bill_specialist", "including sponsors and committee assignments."),
        
        # 3. Committee specialist follows up
        ("ModelClientStreamingChunkEvent", "committee_specialist", "As the committee specialist, "),
        ("ModelClientStreamingChunkEvent", "committee_specialist", "I will analyze the relevant committees "),
        ("ModelClientStreamingChunkEvent", "committee_specialist", "and their members for this investigation."),
        
        # 4. Actions specialist (this should test if non-core agents appear)
        ("ModelClientStreamingChunkEvent", "actions_specialist", "I am analyzing the timeline of actions "),
        ("ModelClientStreamingChunkEvent", "actions_specialist", "for this legislation. "),
        ("ModelClientStreamingChunkEvent", "actions_specialist", "Let me compile the chronological events."),
        
        # 5. Final termination
        ("ModelClientStreamingChunkEvent", "orchestrator", "Investigation complete. "),
        ("ModelClientStreamingChunkEvent", "orchestrator", "All specialists have provided their analysis. "),
        ("ModelClientStreamingChunkEvent", "orchestrator", "TERMINATE"),
    ]
    
    print(f"Processing {len(test_messages)} test messages...")
    print()
    
    # Process messages with realistic timing
    for i, (msg_type, source, content) in enumerate(test_messages):
        print(f"Step {i+1}: {source} - {content[:50]}...")
        
        # Create mock message
        mock_msg = MockMessage(msg_type, source, content)
        
        # Process message
        await accumulator.process_stream_message(mock_msg)
        
        # Simulate realistic token timing (50ms between tokens)
        await asyncio.sleep(0.05)
        
        # Add a longer pause between different agents to trigger finalization
        if i < len(test_messages) - 1:
            next_source = test_messages[i + 1][1]
            if next_source != source:
                print(f"   → Agent switch from {source} to {next_source}, waiting for finalization...")
                await asyncio.sleep(1.0)  # Wait for finalization timeout
    
    # Final finalization
    await accumulator.finish()
    
    print()
    print("🎯 Test Results:")
    print("=" * 50)
    print(f"Total events captured: {len(callback.events)}")
    
    # Analyze events by type
    event_types = {}
    agents_seen = set()
    
    for event in callback.events:
        event_type = event['type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if 'data' in event and 'agent' in event['data']:
            agents_seen.add(event['data']['agent'])
    
    print(f"Event types: {event_types}")
    print(f"Agents seen: {sorted(agents_seen)}")
    
    # Check for missing agents
    expected_agents = {'orchestrator', 'bill_specialist', 'committee_specialist', 'actions_specialist'}
    missing_agents = expected_agents - agents_seen
    if missing_agents:
        print(f"⚠️  Missing agents: {missing_agents}")
    else:
        print("✅ All expected agents appeared")
    
    # Show detailed events
    print("\n📋 Detailed Events:")
    for i, event in enumerate(callback.events):
        timestamp = time.strftime('%H:%M:%S', time.localtime(event['timestamp']))
        agent = event.get('data', {}).get('agent', 'unknown')
        summary = event.get('data', {}).get('simplified', 'No summary')
        print(f"  {i+1:2d}. [{timestamp}] {agent:20} | {summary}")

if __name__ == "__main__":
    asyncio.run(run_simple_test())
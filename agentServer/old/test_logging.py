#!/usr/bin/env python3
"""
Test logging functionality by simulating a real investigation workflow
without starting the WebSocket server. This allows debugging the logging
behavior in isolation.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from silent_buffer_logger import setup_silent_logging, shutdown_logging
from autogen5_websocket import run_full_investigation

class MockWebSocket:
    """Mock WebSocket for testing without actual WebSocket connection"""
    
    def __init__(self):
        self.sent_messages = []
        
    async def send(self, message):
        """Mock send method that stores messages for inspection"""
        print(f"📤 MOCK WebSocket Send: {message}")
        self.sent_messages.append(message)

async def test_investigation_with_logging():
    """Test a real investigation with the same logging as the server"""
    
    print("🧪 Starting investigation logging test...")
    print("📁 Logs will be saved to: logs/")
    print("🔍 This simulates what happens when frontend starts investigation")
    print("=" * 60)
    
    # Setup silent buffer logging (same as server)
    silent_logger = setup_silent_logging()
    logger = logging.getLogger('autogen_server')
    
    # Create mock WebSocket
    mock_websocket = MockWebSocket()
    
    # Simulate investigation data (same as what frontend would send)
    investigation_data = {
        "sessionId": f"test_session_{datetime.now().timestamp()}",
        "company": "ExxonMobil", 
        "bill": "s383-116",
        "description": "Test investigation for logging purposes"
    }
    
    session_id = investigation_data["sessionId"]
    company = investigation_data["company"]
    bill = investigation_data["bill"]
    
    print(f"🔍 Starting test investigation:")
    print(f"   Session ID: {session_id}")
    print(f"   Company: {company}")
    print(f"   Bill: {bill}")
    print("=" * 60)
    
    # Log investigation start (same as server does)
    logger.info(f"🔍 Starting FULL investigation: {session_id}")
    logger.info(f"📋 Investigation params: company={company}, bill={bill}")
    
    try:
        # Run the actual investigation (same as server does)
        print("🚀 Running full investigation...")
        await run_full_investigation(
            company_name=company,
            bill=bill
        )
        
        logger.info(f"✅ Investigation completed successfully: {session_id}")
        
    except Exception as e:
        logger.error(f"❌ Investigation failed: {e}")
        print(f"❌ Investigation error: {e}")
        raise
    
    print("=" * 60)
    print(f"📤 Mock WebSocket received {len(mock_websocket.sent_messages)} messages")
    
    # Show sample of messages sent
    for i, msg in enumerate(mock_websocket.sent_messages[:5]):
        print(f"   Message {i+1}: {msg[:100]}...")
    
    if len(mock_websocket.sent_messages) > 5:
        print(f"   ... and {len(mock_websocket.sent_messages) - 5} more messages")
    
    return session_id

async def main():
    """Main test function"""
    
    print("🧪 AutoGen Investigation Logging Test")
    print("🔄 This tests the same logging that happens in start_server_with_logging.py")
    print("📝 But without starting the WebSocket server")
    print()
    
    session_id = None
    
    try:
        # Run the test investigation
        session_id = await test_investigation_with_logging()
        
        print("=" * 60)
        print("✅ Test investigation completed!")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logging.getLogger('autogen_server').error(f"Test failed: {e}")
    finally:
        # Write buffer to log file (same as server does)
        try:
            print("\n📝 Writing log buffer to file...")
            log_file = shutdown_logging()
            if log_file:
                print(f"✅ Log buffer written to: {log_file}")
                
                # Show log file stats
                if os.path.exists(log_file):
                    file_size = os.path.getsize(log_file)
                    print(f"📊 Log file size: {file_size} bytes")
                    
                    # Show last few lines of log
                    print("\n📋 Last few log entries:")
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        for line in lines[-5:]:
                            print(f"   {line.strip()}")
            else:
                print("⚠️  No log file was created")
                
        except Exception as e:
            print(f"❌ Error writing log buffer: {e}")
    
    print("\n🧪 Test complete!")
    print("💡 To run a real server with this logging, use: python start_server_with_logging.py")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Test stopped gracefully")
    except Exception as e:
        print(f"❌ Test startup error: {e}")
        sys.exit(1)
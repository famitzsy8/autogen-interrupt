#!/usr/bin/env python3
"""
Enhanced server starter with integrated investigation logging
Run this instead of start_server.py to get structured logging

FIXED: Integrates logging directly into async WebSocket server
instead of trying to wrap it as subprocess
"""

import asyncio
import sys
import os
import signal
from pathlib import Path
from datetime import datetime
import logging

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from wsServer import WebSocketServer  
from helper.silentBuffer import setup_silent_logging, shutdown_logging

class LoggingWebSocketServer(WebSocketServer):
    """Enhanced WebSocket server with silent buffer logging"""
    
    def __init__(self, host="localhost", port=8760):
        # Setup silent buffer logging BEFORE calling parent constructor
        self.silent_logger = setup_silent_logging()
        
        super().__init__(host, port)
        
        print(f"🚀 Starting AutoGen WebSocket Server with silent buffer logging...")
        print(f"📍 Server will be available at: ws://{host}:{port}")
        
    async def start_investigation(self, websocket, data: dict):
        """Enhanced investigation with real-time logging"""
        session_id = data.get("sessionId", f"session_{str(datetime.now().timestamp())}")
        
        # Log investigation start
        logger = logging.getLogger('autogen_server')
        logger.info(f"🔍 Starting investigation: {session_id}")
        
        try:
            await super().start_investigation(websocket, data)
        except Exception as e:
            logger.error(f"❌ Investigation failed: {e}")
            raise
    
    async def start_full_investigation(self, websocket, data: dict):
        """Enhanced full investigation with silent buffer logging"""
        session_id = data.get("sessionId", f"session_{datetime.now().timestamp()}")
        
        # Log full investigation start (silent - goes to buffer)
        import logging
        logger = logging.getLogger('autogen_server')
        logger.info(f"🔍 Starting FULL investigation: {session_id}")
        
        try:
            await super().start_full_investigation(websocket, data)
        except Exception as e:
            logger.error(f"❌ Full investigation failed: {e}")
            raise

async def main():
    """Main async entry point with logging"""
    server_instance = None
    server = None
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down server...")
        
        try:
            # Write buffer to log file
            log_file = shutdown_logging()
            if log_file:
                print(f"✅ Buffer written to: {log_file}")
        except Exception as e:
            print(f"Error writing log buffer: {e}")
        
        # Force immediate shutdown
        print("✅ Server shutdown complete")
        os._exit(0)
        
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Starting AutoGen WebSocket Server with integrated logging...")
    print("📁 Logs saved to: logs/")
    print("📍 Server will be available at: ws://localhost:8766")
    print("🔗 frontend_demo should connect to this address")
    print("🐳 Connecting to ragmcp server in Docker container")
    print("⚠️  Make sure Docker container 'ragmcp_server' is running")
    print("   Use: docker start ragmcp_server")
    print("🔍 Press Ctrl+C to stop and view report")
    print("=" * 50)
    
    try:
        # Create and start the enhanced server
        server_instance = LoggingWebSocketServer(host="0.0.0.0", port=8766)
        
        # Start the server (returns websockets server object)
        server = await server_instance.start_server()
        
        # Keep the server running forever until interrupted
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            print("\n🛑 Server task cancelled")
        
    except KeyboardInterrupt:
        print("\n✅ Server shutdown gracefully")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        # Clean up any active investigations
        if server_instance:
            try:
                for session_id, task in server_instance.active_investigations.items():
                    task.cancel()
            except Exception as e:
                print(f"Error during cleanup: {e}")
        
        # Write buffer to log file
        try:
            log_file = shutdown_logging()
            if log_file:
                print(f"✅ Buffer written to: {log_file}")
        except Exception as e:
            print(f"Error writing log buffer: {e}")
        
        if server:
            try:
                server.close()
                await server.wait_closed()
            except Exception as e:
                print(f"Error closing server: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Server shutdown gracefully")
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        sys.exit(1)
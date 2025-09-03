#!/usr/bin/env python3
"""
Simple server starter - GUARANTEED to terminate on Ctrl+C
Use this if start_server_with_logging.py won't shut down properly
"""

import asyncio
import sys
import os
import signal
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from websocket_server import main as original_main

# Global flag for shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    print(f"\n🛑 Received signal {signum}, shutting down server...")
    shutdown_requested = True
    
    # Force exit after 2 seconds if graceful shutdown doesn't work
    def force_exit():
        import time
        time.sleep(2)
        print("🔨 Forcing immediate shutdown...")
        os._exit(0)
    
    import threading
    threading.Thread(target=force_exit, daemon=True).start()

async def main_with_forced_shutdown():
    """Main function with guaranteed shutdown"""
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Starting AutoGen WebSocket Server (Simple Mode)...")
    print("📍 Server will be available at: ws://localhost:8766")
    print("🔗 frontend_demo should connect to this address")
    print("🐳 Connecting to ragmcp server in Docker container")
    print("⚠️  Make sure Docker container 'congressmcp_service' is running")
    print("   Use: docker start congressmcp_service")
    print("🔍 Press Ctrl+C to stop (GUARANTEED termination)")
    print("=" * 50)
    
    try:
        # Run the original server
        await original_main()
    except KeyboardInterrupt:
        print("\n✅ Server shutdown gracefully")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)
    finally:
        print("🛑 Server stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main_with_forced_shutdown())
    except KeyboardInterrupt:
        print("\n✅ Server shutdown gracefully")
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        sys.exit(1)
    finally:
        # Absolutely force exit
        print("🔚 Forcing final exit...")
        os._exit(0)
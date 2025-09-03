#!/usr/bin/env python3
"""
Startup script for the AutoGen WebSocket server.
This script starts the WebSocket server that bridges the frontend_demo with AutoGen.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from websocket_server import main

if __name__ == "__main__":
    print("🚀 Starting AutoGen WebSocket Server...")
    print("📍 Server will be available at: ws://localhost:8766")
    print("🔗 frontend_demo should connect to this address")
    print("🐳 Connecting to ragmcp server in Docker container")
    print("⚠️  Make sure Docker container 'congressmcp_service' is running")
    print("   Use: docker start congressmcp_service")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Server shutdown gracefully")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)
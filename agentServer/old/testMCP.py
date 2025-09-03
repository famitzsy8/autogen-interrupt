#!/usr/bin/env python3
"""
Minimal MCP connection test to debug ragmcp crashes.
"""
import asyncio
import os
import sys
from autogen_ext.tools.mcp import McpWorkbench, SseServerParams


async def test_mcp_connection():
    print("=== MCP Connection Test Starting ===")
    
    # Setup - same as autogen5.py
    ragmcp_base_url = os.getenv("RAGMCP_URL", "https://ragmcp:8080")
    ragmcp_sse_url = f"{ragmcp_base_url}/sse"
    
    print(f"Connecting to: {ragmcp_sse_url}")
    
    params = SseServerParams(
        url=ragmcp_sse_url,
        timeout=60,
    )
    
    print("Created SSE parameters...")
    
    try:
        print("Creating McpWorkbench...")
        async with McpWorkbench(server_params=params) as workbench:
            print("✅ McpWorkbench created successfully!")
            
            print("Listing available tools...")
            tools = await workbench.list_tools()
            print(f"✅ Found {len(tools)} tools: {[tool.name for tool in tools]}")
            
            print("Testing a simple tool call...")
            if tools:
                first_tool = tools[0]
                print(f"Testing tool: {first_tool.name}")
                # Just list, don't actually call
                print(f"Tool description: {first_tool.description}")
            
            print("✅ MCP connection test completed successfully!")
            
    except Exception as e:
        print(f"❌ MCP connection failed: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    print("Python version:", sys.version)
    print("Current working directory:", os.getcwd())
    print("Environment RAGMCP_URL:", os.getenv("RAGMCP_URL", "NOT SET"))
    print()
    
    try:
        result = asyncio.run(test_mcp_connection())
        if result:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 Test failed!")
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
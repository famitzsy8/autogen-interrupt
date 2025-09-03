#!/usr/bin/env python3
"""
Test script to verify MCP server connectivity before running the full investigation.
"""

import asyncio
from autogen_ext.tools.mcp import McpWorkbench, StreamableHttpServerParams

async def test_mcp_connection():
    """Test direct connection to the ragmcp server"""
    print("🔧 Testing MCP Server Connection...")
    print("=" * 50)
    
    # Connect to ragMCP server running in separate Docker container
    import os
    ragmcp_url = os.getenv("RAGMCP_URL", "http://ragmcp:8080")
    params = StreamableHttpServerParams(
        url=ragmcp_url,
        timeout_seconds=60,
    )
    
    workbench = None
    try:
        print("📡 Creating MCP workbench...")
        workbench = McpWorkbench(server_params=params)
        
        print("🔗 Initializing MCP connection...")
        await workbench.initialize()
        
        print("📋 Listing available tools...")
        tools = await workbench.list_tools()
        
        print(f"✅ Success! Found {len(tools)} tools:")
        for tool in tools:
            tool_name = tool.get('name', 'Unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'Unknown')
            print(f"  - {tool_name}")
        
        # Test a simple tool call
        print("\n🔧 Testing a simple tool call...")
        try:
            # Test getBillCommittees with proper arguments
            result = await workbench.call_tool("getBillCommittees", {
                "congress_index": {
                    "congress": 117,
                    "bill_type": "hr", 
                    "bill_number": 2307
                }
            })
            print("✅ Tool call successful!")
            print(f"📊 Result preview: {str(result)[:200]}...")
            
        except Exception as tool_error:
            print(f"⚠️  Tool call failed: {tool_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP Connection failed: {e}")
        print(f"💡 Error type: {type(e).__name__}")
        
        # Check if Docker container is accessible
        print("\n🐳 Checking Docker container accessibility...")
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "exec", "congressmcp_service", "python", "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print(f"✅ Docker container accessible: {result.stdout.strip()}")
            else:
                print(f"❌ Docker exec failed: {result.stderr}")
        except Exception as docker_error:
            print(f"❌ Docker test failed: {docker_error}")
        
        return False
        
    finally:
        if workbench:
            try:
                await workbench.close()
                print("🔒 MCP workbench closed")
            except:
                pass

async def main():
    success = await test_mcp_connection()
    
    if success:
        print("\n🎉 MCP connection test PASSED!")
        print("✅ Ready to run AutoGen investigations")
    else:
        print("\n💥 MCP connection test FAILED!")
        print("❌ Fix MCP issues before running investigations")
        
        print("\n🔧 Troubleshooting steps:")
        print("1. Ensure Docker container is running: docker ps")
        print("2. Check ragmcp server: docker exec congressmcp_service python /app/ragmcp/main.py --help")
        print("3. Verify dependencies in container")

if __name__ == "__main__":
    asyncio.run(main())
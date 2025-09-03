#!/usr/bin/env python3
"""
Test script to verify Docker container connectivity and ragmcp server accessibility.
"""

import subprocess
import sys

def test_docker_container():
    """Test if Docker container is running and accessible"""
    print("🐳 Testing Docker container connectivity...")
    
    try:
        # Check if container is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if 'congressmcp_service' not in result.stdout:
            print("❌ Docker container 'congressmcp_service' is not running")
            print("💡 Start it with: docker start congressmcp_service")
            return False
        
        print("✅ Docker container 'congressmcp_service' is running")
        
        # Test Python accessibility
        result = subprocess.run(
            ['docker', 'exec', 'congressmcp_service', 'python', '--version'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Python available in container: {result.stdout.strip()}")
        else:
            print("❌ Python not accessible in container")
            return False
        
        # Test ragmcp directory
        result = subprocess.run(
            ['docker', 'exec', 'congressmcp_service', 'ls', '/app/ragmcp/main.py'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print("✅ ragmcp main.py found in container")
        else:
            print("❌ ragmcp main.py not found in container")
            return False
        
        print("🎉 All Docker connectivity tests passed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error testing Docker: {e}")
        return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False

def main():
    print("🔧 AutoGen Server Docker Connectivity Test")
    print("=" * 50)
    
    if test_docker_container():
        print("\n✅ Ready to start AutoGen WebSocket server!")
        print("Run: python start_server.py")
    else:
        print("\n❌ Please fix Docker issues before starting the server")
        sys.exit(1)

if __name__ == "__main__":
    main()
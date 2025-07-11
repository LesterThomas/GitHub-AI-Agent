#!/usr/bin/env python3
"""
Test script to verify AIVA MCP server connection.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from github_ai_agent.mcp_client import MCPClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_aiva_connection():
    """Test AIVA MCP server connection."""
    print("Testing AIVA MCP server connection...")
    
    mcp_client = None
    try:
        # Initialize MCP client
        mcp_client = MCPClient("mcp_config.json")
        
        # Load configuration
        mcp_client.load_config()
        print(f"✓ Configuration loaded: {len(mcp_client.server_configs)} servers")
        
        # Check if AIVA server is configured
        if "aiva" not in mcp_client.server_configs:
            print("✗ AIVA server not found in configuration")
            return
            
        print("✓ AIVA server configuration found")
        
        # Try to connect to AIVA server
        success = await mcp_client.start_server("aiva")
        if success:
            print("✓ Successfully connected to AIVA server")
            
            # Try to discover tools
            tools = await mcp_client.discover_tools("aiva")
            print(f"✓ Discovered {len(tools)} tools from AIVA")
            
            # List discovered tools
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
                
        else:
            print("✗ Failed to connect to AIVA server")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        if mcp_client:
            try:
                print("Cleaning up...")
                await mcp_client.cleanup_async()
                print("✓ Cleanup completed successfully")
            except Exception as e:
                print(f"Warning: Cleanup error: {e}")


def main():
    """Main test function."""
    print("=" * 60)
    print("AIVA MCP Server Connection Test")
    print("=" * 60)
    
    try:
        asyncio.run(test_aiva_connection())
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

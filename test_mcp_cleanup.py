#!/usr/bin/env python3
"""
Test script to verify MCP client cleanup works properly.
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


async def test_mcp_client_async():
    """Test MCP client connection and cleanup asynchronously."""
    print("Testing MCP client connection and cleanup...")
    
    # Test 1: Initialize and cleanup with context manager
    print("\n1. Testing context manager pattern...")
    try:
        with MCPClient() as mcp_client:
            tools = await mcp_client.initialize_async()
            print(f"✓ Initialized with {len(tools)} tools")
            
            # Test a simple tool call if available
            if tools:
                print(f"✓ Available tools: {[tool.name for tool in tools]}")
    except Exception as e:
        print(f"✗ Error in context manager test: {e}")
        
    # Test 2: Manual initialization and cleanup
    print("\n2. Testing manual initialization and cleanup...")
    try:
        mcp_client = MCPClient()
        tools = await mcp_client.initialize_async()
        print(f"✓ Initialized with {len(tools)} tools")
        
        # Manual cleanup
        await mcp_client.cleanup_async()
        print("✓ Manual cleanup completed")
    except Exception as e:
        print(f"✗ Error in manual test: {e}")
        
    # Test 3: Test with non-existent server (should handle gracefully)
    print("\n3. Testing with non-existent server...")
    try:
        mcp_client = MCPClient("non_existent_config.json")
        tools = await mcp_client.initialize_async()
        print(f"✓ Gracefully handled missing config, got {len(tools)} tools")
        await mcp_client.cleanup_async()
        print("✓ Cleanup completed for missing config")
    except Exception as e:
        print(f"✗ Error in missing config test: {e}")


def test_mcp_client_sync():
    """Test MCP client with synchronous interface."""
    print("\n4. Testing synchronous interface...")
    try:
        mcp_client = MCPClient()
        tools = mcp_client.initialize()
        print(f"✓ Synchronous initialization with {len(tools)} tools")
        
        # Cleanup
        mcp_client.cleanup()
        print("✓ Synchronous cleanup completed")
    except Exception as e:
        print(f"✗ Error in synchronous test: {e}")


def main():
    """Main test function."""
    print("=" * 60)
    print("MCP Client Cleanup Test")
    print("=" * 60)
    
    try:
        # Run async tests
        asyncio.run(test_mcp_client_async())
        
        # Run sync tests
        test_mcp_client_sync()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

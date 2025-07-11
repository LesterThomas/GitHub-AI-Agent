#!/usr/bin/env python3
"""
Test script to verify the AIVA tool argument mapping fix.
"""

import asyncio
import json
import logging
import sys
import warnings
from pathlib import Path

# Suppress MCP SDK cleanup warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, 
                       message=".*unhandled exception during asyncio.run.*")

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from github_ai_agent.mcp_client import MCPClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_aiva_tool_arguments():
    """Test the AIVA tool with different argument patterns."""
    print("=" * 60)
    print("AIVA Tool Argument Mapping Test")
    print("=" * 60)
    
    try:
        # Initialize MCP client
        mcp_client = MCPClient("mcp_config.json")
        tools = mcp_client.initialize()
        
        # Find the AIVA tool
        aiva_tool = None
        for tool in tools:
            if 'aiva' in tool.name:
                aiva_tool = tool
                break
        
        if not aiva_tool:
            print("✗ AIVA tool not found!")
            return False
        
        print(f"✓ Found AIVA tool: {aiva_tool.name}")
        print(f"Description: {aiva_tool.description}")
        
        # Test 1: Test with proper keyword argument
        print("\n1. Testing with proper keyword argument...")
        try:
            result = aiva_tool.func(query="What is TM Forum?")
            result_data = json.loads(result)
            if result_data.get('success'):
                print("✓ Keyword argument test passed")
                content = result_data.get('content', [])
                if content:
                    print(f"  Response preview: {str(content[0])[:100]}...")
            else:
                print(f"✗ Keyword argument test failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"✗ Keyword argument test failed with exception: {e}")
        
        # Test 2: Test with generic argument (simulating LangChain behavior)  
        print("\n2. Testing with generic argument (__arg1)...")
        try:
            result = aiva_tool.func(__arg1="What is ODA?")
            result_data = json.loads(result)
            if result_data.get('success'):
                print("✓ Generic argument test passed")
                content = result_data.get('content', [])
                if content:
                    print(f"  Response preview: {str(content[0])[:100]}...")
            else:
                print(f"✗ Generic argument test failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"✗ Generic argument test failed with exception: {e}")
        
        # Test 3: Test with positional argument
        print("\n3. Testing with positional argument...")
        try:
            result = aiva_tool.func("What is TMF Open API?")
            result_data = json.loads(result)
            if result_data.get('success'):
                print("✓ Positional argument test passed")
                content = result_data.get('content', [])
                if content:
                    print(f"  Response preview: {str(content[0])[:100]}...")
            else:
                print(f"✗ Positional argument test failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"✗ Positional argument test failed with exception: {e}")
        
        # Cleanup
        mcp_client.cleanup()
        
        print("\n" + "=" * 60)
        print("✓ AIVA tool argument mapping test completed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    try:
        success = test_aiva_tool_arguments()
        if success:
            print("\n🎉 All tests completed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

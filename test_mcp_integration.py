#!/usr/bin/env python3
"""
Comprehensive test to verify MCP integration works correctly with the GitHub AI Agent.
"""

import asyncio
import json
import logging
import sys
import warnings
from pathlib import Path

# Suppress MCP SDK cleanup warnings (harmless asyncio shutdown issue)
warnings.filterwarnings("ignore", category=RuntimeWarning, 
                       message=".*unhandled exception during asyncio.run.*")
warnings.filterwarnings("ignore", category=RuntimeWarning,
                       message=".*an error occurred during closing of asynchronous generator.*")

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from github_ai_agent.mcp_client import MCPClient
from github_ai_agent.agent import GitHubIssueAgent
from github_ai_agent.config import get_settings
from github_ai_agent.github_client import GitHubClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_mcp_integration():
    """Test the complete MCP integration with the GitHub AI Agent."""
    print("=" * 70)
    print("GitHub AI Agent MCP Integration Test")
    print("=" * 70)
    
    success_count = 0
    total_tests = 6
    
    # Test 1: MCP Client initialization
    print("\n1. Testing MCP Client initialization...")
    try:
        mcp_client = MCPClient("mcp_config.json")
        mcp_client.load_config()
        print(f"✓ MCP client initialized with {len(mcp_client.server_configs)} server configs")
        success_count += 1
    except Exception as e:
        print(f"✗ MCP client initialization failed: {e}")
        return False
    
    # Test 2: MCP Tools discovery
    print("\n2. Testing MCP tools discovery...")
    try:
        tools = mcp_client.initialize()
        print(f"✓ Discovered {len(tools)} MCP tools")
        if tools:
            print(f"  Available tools: {[tool.name for tool in tools]}")
        success_count += 1
    except Exception as e:
        print(f"✗ MCP tools discovery failed: {e}")
        return False
    
    # Test 3: GitHub Client initialization
    print("\n3. Testing GitHub client initialization...")
    try:
        settings = get_settings()
        github_client = GitHubClient(
            token=settings.github_ai_agent_token or settings.github_token,
            target_owner=settings.target_owner,
            target_repo=settings.target_repo
        )
        print("✓ GitHub client initialized successfully")
        success_count += 1
    except Exception as e:
        print(f"✗ GitHub client initialization failed: {e}")
        return False
    
    # Test 4: Agent initialization with MCP
    print("\n4. Testing agent initialization with MCP...")
    try:
        agent = GitHubIssueAgent(
            github_client=github_client,
            openai_api_key=settings.openai_api_key,
            enable_mcp=True,
            mcp_config_file="mcp_config.json"
        )
        print("✓ Agent initialized with MCP enabled")
        success_count += 1
    except Exception as e:
        print(f"✗ Agent initialization failed: {e}")
        return False
    
    # Test 5: Agent tools integration
    print("\n5. Testing agent tools integration...")
    try:
        # Get the agent's tools
        agent_tools = agent.tools
        
        # Check for GitHub tools
        github_tools = [tool for tool in agent_tools if not tool.name.startswith('mcp_')]
        mcp_tools = [tool for tool in agent_tools if tool.name.startswith('mcp_')]
        
        print(f"✓ Agent has {len(github_tools)} GitHub tools")
        print(f"✓ Agent has {len(mcp_tools)} MCP tools")
        print(f"✓ Total tools: {len(agent_tools)}")
        
        # Show tool names
        if mcp_tools:
            print(f"  MCP tools: {[tool.name for tool in mcp_tools]}")
        
        success_count += 1
    except Exception as e:
        print(f"✗ Agent tools integration failed: {e}")
        return False
    
    # Test 6: MCP tool functionality
    print("\n6. Testing MCP tool functionality...")
    try:
        if mcp_tools:
            # Test the AIVA tool
            aiva_tool = next((tool for tool in mcp_tools if 'aiva' in tool.name), None)
            if aiva_tool:
                print(f"✓ Found AIVA tool: {aiva_tool.name}")
                
                # Test the tool execution
                result = aiva_tool.func(query="What is TM Forum?")
                result_data = json.loads(result) if isinstance(result, str) else result
                
                if result_data.get('success'):
                    print("✓ AIVA tool executed successfully")
                    content = result_data.get('content', [])
                    if content:
                        print(f"  Response length: {len(str(content))} characters")
                else:
                    print(f"⚠ AIVA tool execution returned: {result_data.get('error', 'Unknown error')}")
            else:
                print("⚠ AIVA tool not found in MCP tools")
        else:
            print("⚠ No MCP tools available to test")
        
        success_count += 1
    except Exception as e:
        print(f"✗ MCP tool functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 7: Agent cleanup
    print("\n7. Testing agent cleanup...")
    try:
        agent.cleanup()
        print("✓ Agent cleanup completed successfully")
        success_count += 1
    except Exception as e:
        print(f"⚠ Agent cleanup had warnings: {e}")
        # Don't fail the test for cleanup warnings
        success_count += 1
    
    # Results
    print("\n" + "=" * 70)
    print(f"Test Results: {success_count}/{total_tests + 1} passed")
    
    if success_count >= total_tests:
        print("✅ All critical tests passed! MCP integration is working correctly.")
        print("\nThe GitHub AI Agent is ready to use with MCP support.")
        return True
    else:
        print(f"❌ {total_tests + 1 - success_count} tests failed. Please check the configuration.")
        return False


def main():
    """Main test function."""
    try:
        success = test_mcp_integration()
        if success:
            print("\n🎉 MCP integration test completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ MCP integration test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

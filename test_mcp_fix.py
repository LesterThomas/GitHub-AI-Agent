#!/usr/bin/env python3

import sys
import os

sys.path.append(os.path.dirname(__file__))

from github_ai_agent.mcp_client import MCPClient
import json


def test_mcp_tool_fix():
    print("Testing MCP tool fix...")

    # Initialize the client
    client = MCPClient("mcp_config.json")
    tools = client.initialize()

    print(f"Loaded {len(tools)} tools")

    if tools:
        tool = tools[0]
        print(f"Tool name: {tool.name}")
        print(f"Tool description: {tool.description}")

        # Test the positional argument that was failing
        print("\nTesting positional argument:")
        try:
            result = tool.func(
                "Overview of Open Digital Architecture (ODA) and its components."
            )
            parsed_result = json.loads(result)
            print("✅ SUCCESS! Tool call completed without errors")
            print(f"Success: {parsed_result.get('success')}")
            print(f"Response: {parsed_result.get('response', 'No response')[:100]}...")
        except Exception as e:
            print(f"❌ ERROR: {e}")

        # Test keyword argument
        print("\nTesting keyword argument:")
        try:
            result = tool.func(query="What is TM Forum Open API?")
            parsed_result = json.loads(result)
            print("✅ SUCCESS! Keyword argument works")
            print(f"Success: {parsed_result.get('success')}")
        except Exception as e:
            print(f"❌ ERROR: {e}")

    client.cleanup()
    print("Test completed!")


if __name__ == "__main__":
    test_mcp_tool_fix()

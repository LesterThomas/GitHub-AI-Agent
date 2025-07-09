#!/usr/bin/env python3
"""
Test script to verify the specific AIVA tool calling scenario that was failing.
This reproduces the exact error condition that was reported.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from github_ai_agent.mcp_client import MCPClient, MCPTool
from langchain_core.tools import Tool
import json


def test_aiva_tool_specific_scenario():
    print("🧪 Testing AIVA tool with specific scenario that was failing...")

    # Create an MCP client instance
    client = MCPClient("mcp_config.json")
    client.load_config()

    # Create a mock AIVA tool matching the exact scenario
    aiva_tool = MCPTool(
        name="query_tmforum_ai_assistant",
        description="Get information from the TM Forum knowledge base using AIVA AI Assistant.",
        server_name="aiva",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A natural language question about TM Forum topics",
                }
            },
            "required": ["query"],
        },
    )

    # Add the tool to available tools
    client.available_tools = [aiva_tool]

    # Create LangChain tools
    langchain_tools = client.create_langchain_tools()

    print(f"✅ Created {len(langchain_tools)} LangChain tools")

    if langchain_tools:
        tool = langchain_tools[0]
        print(f"📋 Tool name: {tool.name}")
        print(f"📝 Tool description: {tool.description}")

        # Test the exact scenario that was failing:
        # LangChain calling with the pattern shown in the error log
        test_query = "Overview of Open Digital Architecture (ODA) and its components."

        print(f"\n🔬 Testing with query: {test_query}")

        try:
            # This simulates how LangChain calls the tool with a positional argument
            # The original error was: tool_func() takes 0 positional arguments but 1 was given
            result = tool.func(test_query)

            # Parse and display the result
            parsed_result = json.loads(result)
            print("✅ SUCCESS! Tool call completed without TypeError")
            print(f"🎯 Success: {parsed_result.get('success')}")

            if parsed_result.get("success"):
                response = parsed_result.get(
                    "response", parsed_result.get("result", "No response")
                )
                print(f"📄 Response preview: {str(response)[:100]}...")
            else:
                print(f"❌ Tool returned error: {parsed_result.get('error')}")

        except TypeError as e:
            print(f"❌ FAILED! Still getting TypeError: {e}")
        except Exception as e:
            print(f"⚠️  Other error (but not TypeError): {e}")

    print("\n🧹 Cleaning up...")
    client.cleanup()
    print("✅ Test completed!")


if __name__ == "__main__":
    test_aiva_tool_specific_scenario()

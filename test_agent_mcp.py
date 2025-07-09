#!/usr/bin/env python3

import sys
import os

sys.path.append(os.path.dirname(__file__))

from github_ai_agent.agent import GitHubIssueAgent
import json


def test_agent_with_mcp():
    print("Testing GitHub AI Agent with MCP integration...")

    try:
        # Initialize the agent
        agent = GitHubIssueAgent()

        print(f"Agent initialized successfully")
        print(f"Available tools: {len(agent.tools)}")

        # Find the MCP tool
        mcp_tools = [tool for tool in agent.tools if tool.name.startswith("mcp_")]
        print(f"MCP tools available: {len(mcp_tools)}")

        if mcp_tools:
            tool = mcp_tools[0]
            print(f"Testing MCP tool: {tool.name}")

            # Test the tool call that was previously failing
            try:
                result = tool.func("What is Open Digital Architecture?")
                parsed_result = json.loads(result)
                print("✅ SUCCESS! MCP tool integration working correctly")
                print(f"Tool response success: {parsed_result.get('success')}")
                if "response" in parsed_result:
                    print(f"Response preview: {parsed_result['response'][:100]}...")
                elif "result" in parsed_result:
                    print(f"Result preview: {str(parsed_result['result'])[:100]}...")
            except Exception as e:
                print(f"❌ ERROR calling MCP tool: {e}")

        # Cleanup
        if hasattr(agent, "mcp_client") and agent.mcp_client:
            agent.mcp_client.cleanup()

        print("Agent MCP integration test completed!")

    except Exception as e:
        print(f"❌ ERROR initializing agent: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_agent_with_mcp()

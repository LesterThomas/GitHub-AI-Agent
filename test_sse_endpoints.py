#!/usr/bin/env python3
"""
Test script to verify the SSE endpoint separation functionality.
This verifies that the MCP client properly constructs /sse and /messages endpoints.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from github_ai_agent.mcp_client import MCPClient
import json


def test_sse_endpoint_separation():
    print("🧪 Testing SSE endpoint separation...")

    # Create an MCP client instance
    client = MCPClient("mcp_config.json")
    client.load_config()

    print(f"✅ Loaded {len(client.server_configs)} server configurations")

    if "aiva" in client.server_configs:
        aiva_config = client.server_configs["aiva"]
        print(f"📋 AIVA config:")
        print(f"   Type: {aiva_config.server_type}")
        print(f"   Base URL: {aiva_config.url}")

        # Start the SSE server connection
        if client.start_server("aiva"):
            print("✅ Successfully prepared SSE server connection")

            # Check the connection info
            if "aiva" in client.sse_connections:
                conn_info = client.sse_connections["aiva"]
                print(f"📡 Connection endpoints:")
                print(f"   Base URL: {conn_info['base_url']}")
                print(f"   SSE URL: {conn_info['sse_url']}")
                print(f"   Messages URL: {conn_info['messages_url']}")

                # Verify the endpoints are constructed correctly
                expected_sse = "http://localhost:8000/sse"
                expected_messages = "http://localhost:8000/messages"

                if conn_info["sse_url"] == expected_sse:
                    print("✅ SSE endpoint constructed correctly")
                else:
                    print(
                        f"❌ SSE endpoint mismatch: expected {expected_sse}, got {conn_info['sse_url']}"
                    )

                if conn_info["messages_url"] == expected_messages:
                    print("✅ Messages endpoint constructed correctly")
                else:
                    print(
                        f"❌ Messages endpoint mismatch: expected {expected_messages}, got {conn_info['messages_url']}"
                    )

            else:
                print("❌ No connection info found for AIVA")

        else:
            print("❌ Failed to prepare SSE server connection")
    else:
        print("❌ No AIVA configuration found")

    print(
        "\n🔬 Testing tool discovery (will attempt to connect to /messages endpoint)..."
    )
    tools = client.discover_tools("aiva")
    print(f"📋 Discovered {len(tools)} tools (including mock fallback)")

    if tools:
        tool = tools[0]
        print(f"🛠️  First tool: {tool.name}")
        print(f"📝 Description: {tool.description}")

    print("\n🧹 Cleaning up...")
    client.cleanup()
    print("✅ Test completed!")


if __name__ == "__main__":
    test_sse_endpoint_separation()

#!/usr/bin/env python3
"""
Test script to verify that session ID is properly included in URL parameters.
This test will mock the HTTP client to capture the actual URLs being requested.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from github_ai_agent.mcp_client import MCPClient, MCPServerConfig
from unittest.mock import Mock, patch
import json


def test_session_id_in_url():
    print("🧪 Testing Session ID in URL parameters...")

    # Create an MCP client instance
    client = MCPClient("mcp_config.json")
    client.load_config()

    # Start the SSE server connection
    if not client.start_server("aiva"):
        print("❌ Failed to start server")
        return

    # Mock the HTTP client to capture requests
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Mcp-Session-Id": "test-session-123"}
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 0,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "test-server", "version": "1.0.0"},
        },
    }

    captured_requests = []

    def capture_post(url, **kwargs):
        captured_requests.append({"url": url, "method": "POST", "kwargs": kwargs})
        return mock_response

    # Patch the HTTP client's post method
    with patch.object(client.http_clients["aiva"], "post", side_effect=capture_post):
        print("📡 Testing initialization with session ID in URL...")

        # First, test initialization (should not have session_id yet)
        connection_info = client.sse_connections["aiva"]
        http_client = client.http_clients["aiva"]
        config = client.server_configs["aiva"]

        # Try to initialize (this should create a session)
        client._initialize_mcp_session("aiva", http_client, config)

        print(f"🔍 Captured {len(captured_requests)} requests:")
        for i, req in enumerate(captured_requests):
            print(f"   Request {i+1}: {req['method']} {req['url']}")

        # Verify the initialization request
        if captured_requests:
            init_request = captured_requests[0]
            expected_url = "http://localhost:8000/messages"
            if init_request["url"] == expected_url:
                print("✅ Initial request URL correct (no session_id)")
            else:
                print(
                    f"❌ Initial request URL incorrect: expected {expected_url}, got {init_request['url']}"
                )

        # Clear captured requests
        captured_requests.clear()

        # Manually set a session ID to test subsequent requests
        client.sse_connections["aiva"]["session_id"] = "test-session-123"

        print("\n🔍 Testing tool discovery with session ID in URL...")

        # Mock response for tools/list
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ]
            },
        }

        # Test tool discovery
        client._discover_tools_sse("aiva", config)

        print(f"🔍 Captured {len(captured_requests)} requests after tool discovery:")
        for i, req in enumerate(captured_requests):
            print(f"   Request {i+1}: {req['method']} {req['url']}")

        # Verify the tools/list request includes session_id in URL
        if captured_requests:
            tools_request = captured_requests[0]
            expected_url = "http://localhost:8000/messages?session_id=test-session-123"
            if tools_request["url"] == expected_url:
                print("✅ Tools/list request URL includes session_id parameter")
            else:
                print(
                    f"❌ Tools/list request URL incorrect: expected {expected_url}, got {tools_request['url']}"
                )

        # Clear captured requests
        captured_requests.clear()

        print("\n🔍 Testing tool call with session ID in URL...")

        # Mock response for tools/call
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"content": "Test tool result"},
        }

        # Test tool call
        client._call_tool_sse("test_tool", "aiva", {"query": "test query"})

        print(f"🔍 Captured {len(captured_requests)} requests after tool call:")
        for i, req in enumerate(captured_requests):
            print(f"   Request {i+1}: {req['method']} {req['url']}")

        # Verify the tools/call request includes session_id in URL
        if captured_requests:
            call_request = captured_requests[0]
            expected_url = "http://localhost:8000/messages?session_id=test-session-123"
            if call_request["url"] == expected_url:
                print("✅ Tools/call request URL includes session_id parameter")
            else:
                print(
                    f"❌ Tools/call request URL incorrect: expected {expected_url}, got {call_request['url']}"
                )

    print("\n🧹 Cleaning up...")
    client.cleanup()
    print("✅ Session ID URL parameter test completed!")


if __name__ == "__main__":
    test_session_id_in_url()

#!/usr/bin/env python3
"""Test script to verify the single tool agent functionality."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_ai_agent.agent import GitHubIssueAgent


def test_single_tool():
    """Test the single create_files_from_request tool."""
    print("=== Testing Single Tool Agent ===")

    # Mock GitHub client for testing
    class MockGitHubClient:
        def __init__(self):
            self.target_owner = "test_owner"
            self.target_repo = "test_repo"

    # Create agent with mock client
    mock_client = MockGitHubClient()
    agent = GitHubIssueAgent(
        github_client=mock_client,
        openai_api_key="test_key",  # Won't be used in tool testing
        model="gpt-4",
        max_iterations=3,
        recursion_limit=5,
    )

    print(f"Agent created with {len(agent.tools)} tool(s)")

    # Check that we have exactly one tool
    assert len(agent.tools) == 1, f"Expected 1 tool, got {len(agent.tools)}"

    tool = agent.tools[0]
    print(f"Tool name: {tool.name}")
    assert (
        tool.name == "create_files_from_request"
    ), f"Expected 'create_files_from_request', got {tool.name}"

    # Test the tool with valid JSON input
    test_input = json.dumps(
        [
            {
                "filename": "test.md",
                "file_content": "# Test File\n\nThis is a test file created by the AI agent.",
            },
            {
                "filename": "readme.txt",
                "file_content": "This is a readme file with some basic information.",
            },
        ]
    )

    print("\n--- Testing Tool with Valid Input ---")
    print(f"Input: {test_input}")

    result = tool.func(test_input)
    print(f"\nOutput: {result}")

    # Parse and validate the result
    try:
        result_data = json.loads(result)
        assert result_data.get("success") is True, "Tool should return success=True"
        assert "files" in result_data, "Result should contain 'files' key"
        assert (
            len(result_data["files"]) == 2
        ), f"Expected 2 files, got {len(result_data['files'])}"

        # Check first file
        file1 = result_data["files"][0]
        assert (
            file1["filename"] == "test.md"
        ), f"Expected 'test.md', got {file1['filename']}"
        assert (
            "Test File" in file1["content"]
        ), "File content should contain expected text"

        # Check second file
        file2 = result_data["files"][1]
        assert (
            file2["filename"] == "readme.txt"
        ), f"Expected 'readme.txt', got {file2['filename']}"
        assert (
            "readme file" in file2["content"]
        ), "File content should contain expected text"

        print("✅ Tool test passed! Output format is correct.")

    except json.JSONDecodeError:
        print("❌ Tool output is not valid JSON")
        return False
    except AssertionError as e:
        print(f"❌ Tool test failed: {e}")
        return False

    # Test with invalid input
    print("\n--- Testing Tool with Invalid Input ---")
    invalid_input = "not json"
    result = tool.func(invalid_input)
    print(f"Invalid input result: {result}")

    try:
        result_data = json.loads(result)
        assert "error" in result_data, "Invalid input should return an error"
        print("✅ Invalid input handling works correctly.")
    except:
        print("❌ Invalid input should still return valid JSON with error")
        return False

    # Test system prompt
    print("\n--- Testing System Prompt ---")
    system_prompt = agent._get_system_prompt()
    print(f"System prompt: {system_prompt[:200]}...")

    assert (
        "create_files_from_request" in system_prompt
    ), "System prompt should mention the tool"
    assert (
        "JSON array" in system_prompt
    ), "System prompt should mention JSON array format"
    assert (
        "filename" in system_prompt and "file_content" in system_prompt
    ), "System prompt should mention required properties"

    print("✅ System prompt contains required information.")

    print("\n=== All Tests Passed! ===")
    print("The agent is properly configured with a single tool that:")
    print("1. Takes a JSON array of file objects")
    print("2. Each object has 'filename' and 'file_content' properties")
    print("3. Returns a JSON object with the files ready for GitHub creation")
    print("4. Handles errors gracefully")
    print("5. Has a proper system prompt with clear instructions")

    return True


if __name__ == "__main__":
    try:
        test_single_tool()
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

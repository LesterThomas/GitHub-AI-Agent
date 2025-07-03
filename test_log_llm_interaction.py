#!/usr/bin/env python3
"""Test script for the updated log_llm_interaction function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "github_ai_agent"))

from github_ai_agent.logging_utils import log_llm_interaction


# Mock message classes to simulate LangChain messages
class MockMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class MockToolCall:
    def __init__(self, name, args=None, tool_call_id=None):
        self.name = name
        self.args = args or {}
        self.id = tool_call_id or f"call_{name}"


def test_log_llm_interaction():
    """Test the log_llm_interaction function with different message types."""

    print("=== Testing log_llm_interaction function ===\n")

    # Test 1: Message with only content
    print("1. Message with content only:")
    content_message = MockMessage(content="This is a simple text message from the LLM.")
    log_llm_interaction(content_message, "CONTENT_ONLY")
    print()

    # Test 2: Message with tool calls only
    print("2. Message with tool calls only:")
    tool_calls = [
        MockToolCall(
            "create_files_from_request",
            {
                "files_json": '[{"filename": "test.md", "file_content": "# Test\\nContent"}]'
            },
            "call_123",
        ),
        MockToolCall("get_repository_info", {"repo": "test-repo"}, "call_456"),
    ]
    tool_message = MockMessage(tool_calls=tool_calls)
    log_llm_interaction(tool_message, "TOOL_CALLS_ONLY")
    print()

    # Test 3: Message with both content and tool calls
    print("3. Message with both content and tool calls:")
    mixed_message = MockMessage(
        content="I'll help you create the files. Let me use the tool to do that.",
        tool_calls=[
            MockToolCall(
                "create_files_from_request",
                {
                    "files_json": '[{"filename": "README.md", "file_content": "# Project\\nDescription"}]'
                },
            )
        ],
    )
    log_llm_interaction(mixed_message, "MIXED_MESSAGE")
    print()

    # Test 4: Empty message
    print("4. Empty message:")
    empty_message = MockMessage()
    log_llm_interaction(empty_message, "EMPTY")
    print()

    # Test 5: String message (fallback)
    print("5. String message (fallback):")
    log_llm_interaction("This is a plain string message", "STRING_FALLBACK")
    print()


if __name__ == "__main__":
    test_log_llm_interaction()

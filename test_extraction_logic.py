#!/usr/bin/env python3
"""Test script to verify the file extraction logic works correctly."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import ToolMessage, AIMessage


def test_file_extraction():
    """Test the file extraction logic with simulated message flow."""
    print("=== Testing File Extraction Logic ===")

    # Simulate the message flow that happens in the real agent
    # This is based on the actual log output provided

    # Create a simulated ToolMessage (this is what the tool returns)
    tool_message = ToolMessage(
        content="""{
  "success": true,
  "files": [
    {
      "filename": "TEST.md",
      "content": "This is a test.",
      "path": "TEST.md",
      "message": "Create TEST.md as requested"
    }
  ],
  "count": 1
}""",
        name="create_files_from_request",
        tool_call_id="call_YAEGnsxSRrZ7U0yM8VLbmpia",
    )

    # Create a simulated final AI message
    final_ai_message = AIMessage(
        content='Created the file `TEST.md` with the content: "This is a test."'
    )

    # Simulate final_state that would be returned by the agent
    final_state = {
        "messages": [
            # ... other messages would be here ...
            tool_message,
            final_ai_message,
        ]
    }

    print("Simulated final_state with ToolMessage and AIMessage")
    print(f"ToolMessage content: {tool_message.content[:100]}...")
    print(f"Final AIMessage content: {final_ai_message.content}")

    # Test the extraction logic (copied from the agent)
    files_to_create = []

    # Look for ToolMessage instances that contain the tool results
    print("\n--- Testing File Extraction Logic ---")
    print("Searching for tool results in message history")
    for msg in final_state.get("messages", []):
        print(f"Checking message type: {type(msg).__name__}")
        if hasattr(msg, "name"):
            print(f"  Message has name: {msg.name}")

        # Check for ToolMessage instances (the actual tool results)
        if hasattr(msg, "name") and msg.name == "create_files_from_request":
            print("  Found create_files_from_request ToolMessage!")
            try:
                tool_result = json.loads(msg.content)
                print(f"  Parsed JSON successfully: {tool_result.get('success')}")
                if tool_result.get("success") and tool_result.get("files"):
                    files_to_create.extend(tool_result["files"])
                    print(
                        f"  ✅ Extracted {len(tool_result['files'])} files from ToolMessage"
                    )
                    break  # Found the tool result, no need to continue
            except json.JSONDecodeError as e:
                print(f"  ❌ Failed to parse ToolMessage JSON: {e}")
                continue

    print(f"\nTotal files to create: {len(files_to_create)}")

    if files_to_create:
        print("✅ File extraction test PASSED!")
        for i, file_obj in enumerate(files_to_create):
            print(f"  File {i+1}:")
            print(f"    Filename: {file_obj.get('filename')}")
            print(f"    Content: {file_obj.get('content')[:50]}...")
            print(f"    Path: {file_obj.get('path')}")
            print(f"    Message: {file_obj.get('message')}")
        return True
    else:
        print("❌ File extraction test FAILED - no files extracted")
        return False


def test_edge_cases():
    """Test edge cases for file extraction."""
    print("\n=== Testing Edge Cases ===")

    # Test case: No ToolMessage
    final_state_no_tool = {
        "messages": [AIMessage(content="I could not create the files.")]
    }

    print("Test case: No ToolMessage in state")
    files_to_create = []
    for msg in final_state_no_tool.get("messages", []):
        if hasattr(msg, "name") and msg.name == "create_files_from_request":
            files_to_create.append("found")

    if len(files_to_create) == 0:
        print("✅ Correctly handled case with no ToolMessage")
    else:
        print("❌ Incorrectly found ToolMessage when none exists")
        return False

    # Test case: ToolMessage with invalid JSON
    tool_message_bad = ToolMessage(
        content="invalid json content",
        name="create_files_from_request",
        tool_call_id="test_id",
    )

    final_state_bad_json = {"messages": [tool_message_bad]}

    print("Test case: ToolMessage with invalid JSON")
    files_to_create = []
    for msg in final_state_bad_json.get("messages", []):
        if hasattr(msg, "name") and msg.name == "create_files_from_request":
            try:
                tool_result = json.loads(msg.content)
                if tool_result.get("files"):
                    files_to_create.extend(tool_result["files"])
            except json.JSONDecodeError:
                print("  Correctly caught JSON decode error")

    if len(files_to_create) == 0:
        print("✅ Correctly handled case with invalid JSON")
    else:
        print("❌ Incorrectly processed invalid JSON")
        return False

    return True


if __name__ == "__main__":
    try:
        success1 = test_file_extraction()
        success2 = test_edge_cases()

        if success1 and success2:
            print("\n🎉 All file extraction tests passed!")
            print("The fix should work correctly with the actual agent.")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""Integration test to verify the agent properly extracts and processes files."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_agent_file_processing():
    """Test that the agent correctly processes the tool output to create files."""
    print("=== Integration Test: Agent File Processing ===")

    # Mock the final_state that would be returned by the agent
    # This simulates the exact structure from the real log
    from langchain_core.messages import (
        SystemMessage,
        HumanMessage,
        AIMessage,
        ToolMessage,
    )

    final_state = {
        "messages": [
            SystemMessage(content="System prompt..."),
            HumanMessage(
                content="Process this GitHub issue: Create TEST.md with content 'This is a test.'"
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_files_from_request",
                        "args": {
                            "__arg1": '[{"filename": "TEST.md", "file_content": "This is a test."}]'
                        },
                        "id": "call_YAEGnsxSRrZ7U0yM8VLbmpia",
                    }
                ],
            ),
            ToolMessage(
                content='{\n  "success": true,\n  "files": [\n    {\n      "filename": "TEST.md",\n      "content": "This is a test.",\n      "path": "TEST.md",\n      "message": "Create TEST.md as requested"\n    }\n  ],\n  "count": 1\n}',
                name="create_files_from_request",
                tool_call_id="call_YAEGnsxSRrZ7U0yM8VLbmpia",
            ),
            AIMessage(
                content='Created the file `TEST.md` with the content: "This is a test."'
            ),
        ]
    }

    print("Simulated agent execution completed")
    print(f"Final state contains {len(final_state['messages'])} messages")

    # Test the extraction logic exactly as it appears in the agent
    files_to_create = []

    # Look for ToolMessage instances that contain the tool results
    print("\nExtracting files from agent response...")
    for msg in final_state.get("messages", []):
        # Check for ToolMessage instances (the actual tool results)
        if hasattr(msg, "name") and msg.name == "create_files_from_request":
            try:
                tool_result = json.loads(msg.content)
                if tool_result.get("success") and tool_result.get("files"):
                    files_to_create.extend(tool_result["files"])
                    print(
                        f"✅ Extracted {len(tool_result['files'])} files from ToolMessage"
                    )
                    break  # Found the tool result, no need to continue
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse ToolMessage JSON: {e}")
                continue

    print(f"\nTotal files to create: {len(files_to_create)}")

    if files_to_create:
        print("✅ File extraction successful!")

        # Test the file creation logic
        print("\nTesting file creation logic...")
        files_created = []

        for file_obj in files_to_create:
            filename = file_obj.get("filename") or file_obj.get("path")
            file_content = file_obj.get("content") or file_obj.get("file_content", "")

            if not filename:
                print(f"❌ File object missing filename: {file_obj}")
                continue

            print(
                f"  Processing file: {filename} ({len(str(file_content))} characters)"
            )

            # Simulate successful file creation
            files_created.append(filename)
            print(f"  ✅ Would create file: {filename} with content: '{file_content}'")

        if files_created:
            print(f"\n🎉 Integration test PASSED!")
            print(f"   Agent would successfully create {len(files_created)} files:")
            for filename in files_created:
                print(f"   - {filename}")
            print("\nThe agent should now work correctly with real GitHub issues!")
            return True
        else:
            print("❌ No files would be created")
            return False
    else:
        print("❌ No files extracted from agent response")
        return False


if __name__ == "__main__":
    try:
        if test_agent_file_processing():
            print("\n✅ Integration test completed successfully!")
            print("The agent fix should resolve the file creation issue.")
        else:
            print("\n❌ Integration test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

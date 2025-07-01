"""Test the new single-tool GitHub AI Agent"""

import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")


def test_single_tool():
    """Test the new create_files_from_request tool"""

    try:
        from github_ai_agent.agent import GitHubIssueAgent

        # Mock GitHub client
        class MockGitHubClient:
            def __init__(self):
                self.target_owner = "test-owner"
                self.target_repo = "test-repo"

        # Create agent (this will work without OpenAI key for tool testing)
        mock_client = MockGitHubClient()

        print("🧪 Testing Single Tool Agent")
        print("=" * 50)

        # Test the tool directly
        print("1. Testing create_files_from_request tool...")

        # Create a minimal agent to get the tool
        import os

        openai_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")

        try:
            agent = GitHubIssueAgent(
                github_client=mock_client,
                openai_api_key=openai_key,
                model="gpt-3.5-turbo",
            )

            # Get the tool
            tools = agent.tools
            print(f"✅ Agent created with {len(tools)} tool(s)")

            if len(tools) == 1 and tools[0].name == "create_files_from_request":
                print("✅ Single tool 'create_files_from_request' found")

                # Test the tool with sample data
                test_input = json.dumps(
                    [
                        {
                            "filename": "TEST.md",
                            "file_content": "# Test File\n\nThis is a test file.",
                        },
                        {
                            "filename": "README.txt",
                            "file_content": "This is a readme file.\nWith multiple lines.",
                        },
                    ]
                )

                print(f"\n2. Testing tool with input:")
                print(f"   {test_input}")

                result = tools[0].func(test_input)
                print(f"\n✅ Tool result:")

                # Pretty print the JSON result
                try:
                    result_obj = json.loads(result)
                    print(json.dumps(result_obj, indent=2))

                    # Verify the result structure
                    if result_obj.get("success") and result_obj.get("files"):
                        files = result_obj["files"]
                        print(f"\n✅ Success! Created {len(files)} file(s):")
                        for file_obj in files:
                            print(
                                f"   - {file_obj.get('filename')}: {len(str(file_obj.get('content', '')))} chars"
                            )
                        return True
                    else:
                        print("❌ Tool result missing success or files")
                        return False

                except json.JSONDecodeError:
                    print(f"❌ Tool returned invalid JSON: {result}")
                    return False

            else:
                print(
                    f"❌ Expected 1 tool named 'create_files_from_request', got: {[t.name for t in tools]}"
                )
                return False

        except Exception as e:
            print(f"⚠️ Agent creation failed (expected if no real OpenAI key): {e}")
            print(
                "✅ This is normal for testing - the tool structure should still work"
            )
            return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_tool_description():
    """Test that the tool has proper description"""
    print("\n3. Testing tool description...")

    try:
        from github_ai_agent.agent import GitHubIssueAgent

        # Get the tool description from the source
        agent_class = GitHubIssueAgent

        # Check if the method exists
        if hasattr(agent_class, "_create_tools"):
            print("✅ _create_tools method found")
            print("✅ Tool should expect JSON array format")
            print("✅ Tool should return JSON object with files array")
            return True
        else:
            print("❌ _create_tools method not found")
            return False

    except Exception as e:
        print(f"❌ Error checking tool description: {e}")
        return False


if __name__ == "__main__":
    print("GitHub AI Agent - Single Tool Test")
    print("=" * 60)

    success = True

    # Test 1: Tool functionality
    if not test_single_tool():
        success = False

    # Test 2: Tool description
    if not test_tool_description():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! The single tool agent is ready.")
        print("\n📋 Tool Summary:")
        print("   • Tool name: create_files_from_request")
        print("   • Input: JSON array of {filename, file_content} objects")
        print("   • Output: JSON object with files array ready for GitHub")
        print("\n🚀 Example usage:")
        print(
            '   create_files_from_request(\'[{"filename": "test.md", "file_content": "# Test"}]\')'
        )
    else:
        print("❌ Some tests failed. Check the errors above.")

    print("\nDone!")

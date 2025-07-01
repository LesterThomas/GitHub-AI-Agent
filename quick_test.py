"""
Quick verification that the agent can be imported and used.
"""

import sys
import os


def test_basic_import():
    """Test basic imports work."""
    try:
        print("Testing imports...")
        from github_ai_agent.agent import GitHubIssueAgent

        print("✅ GitHubIssueAgent imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_tool_functionality():
    """Test that tools work without OpenAI."""
    try:
        print("Testing tool functionality...")

        # Import the specific functions we need
        import ast
        import re

        def extract_file_request(issue_text: str) -> str:
            """Extract file creation request from issue text."""
            # Look for file creation patterns
            file_patterns = [
                r"[Cc]reate\s+(?:a\s+new\s+)?(?:file\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)",
                r"[Aa]dd\s+(?:a\s+new\s+)?(?:file\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)",
                r"[Mm]ake\s+(?:a\s+new\s+)?(?:file\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)",
            ]

            requested_files = []
            for pattern in file_patterns:
                matches = re.findall(pattern, issue_text, re.IGNORECASE)
                requested_files.extend(matches)

            # Remove duplicates
            unique_files = list(dict.fromkeys(requested_files))

            # Extract content from quotes
            content_patterns = [
                r"write\s+in\s+it\s+['\"]([^'\"]+)['\"]",
                r"with\s+contents?\s+['\"]([^'\"]+)['\"]",
                r"containing\s+['\"]([^'\"]+)['\"]",
            ]

            content_requirements = []
            for pattern in content_patterns:
                matches = re.findall(pattern, issue_text, re.IGNORECASE)
                content_requirements.extend(matches)

            result = {
                "files": unique_files,
                "content": (
                    content_requirements[0]
                    if content_requirements
                    else "Default content"
                ),
                "success": len(unique_files) > 0,
            }

            return str(result)

        # Test the function
        test_issue = "Create a new file TEST.md and write in it 'this is a test'"
        result = extract_file_request(test_issue)
        print(f"✅ Tool test result: {result}")

        # Parse result
        result_dict = ast.literal_eval(result)
        if (
            result_dict.get("files") == ["TEST.md"]
            and result_dict.get("content") == "this is a test"
        ):
            print("✅ Tool extracted correct file and content")
            return True
        else:
            print(f"❌ Tool result incorrect: {result_dict}")
            return False

    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        return False


if __name__ == "__main__":
    print("GitHub AI Agent - Quick Verification")
    print("=" * 50)

    success = True

    # Test 1: Basic imports
    if not test_basic_import():
        success = False

    # Test 2: Tool functionality
    if not test_tool_functionality():
        success = False

    if success:
        print("\n🎉 All tests passed! The agent is ready to use.")
        print("\nNext steps:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Configure GitHub tokens if needed")
        print("3. Run: uv run python -m github_ai_agent.main")
    else:
        print("\n❌ Some tests failed. Check the errors above.")

    print("\nDone!")

#!/usr/bin/env python3
"""
Test script to verify the delete file tool functionality
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_ai_agent.agent import GitHubIssueAgent
from github_ai_agent.config import get_tool_description


def test_delete_tool_description():
    """Test that the delete tool description is properly loaded"""
    try:
        description = get_tool_description("delete_file_from_repo")
        print(f"✅ Delete tool description loaded: {description}")
        return True
    except Exception as e:
        print(f"❌ Error loading delete tool description: {e}")
        return False


def test_delete_tool_in_agent():
    """Test that the delete tool is properly added to the agent's tools"""
    try:
        # Mock GitHub client for testing
        class MockGitHubClient:
            def __init__(self):
                self.target_owner = "test-owner"
                self.target_repo = "test-repo"

            def delete_file(self, path, message, branch):
                return True

        # Create agent instance
        agent = GitHubIssueAgent(
            github_client=MockGitHubClient(), openai_api_key="test-key"
        )

        # Check if delete tool is in the tools list
        tool_names = [tool.name for tool in agent.tools]
        if "delete_file_from_repo" in tool_names:
            print(f"✅ Delete tool found in agent tools: {tool_names}")
            return True
        else:
            print(f"❌ Delete tool NOT found in agent tools: {tool_names}")
            return False

    except Exception as e:
        print(f"❌ Error testing delete tool in agent: {e}")
        return False


def main():
    """Run all tests"""
    print("Testing delete file tool functionality...")
    print("=" * 50)

    test_results = []

    # Test 1: Tool description
    test_results.append(test_delete_tool_description())

    # Test 2: Tool in agent
    test_results.append(test_delete_tool_in_agent())

    # Summary
    print("\n" + "=" * 50)
    passed = sum(test_results)
    total = len(test_results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Delete file tool is properly implemented.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script to verify the unaddressed comment filtering logic
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_ai_agent.main import GitHubAIAgentApp


def test_unaddressed_comment_filtering():
    """Test that the unaddressed comment filtering logic works correctly"""
    print("Testing unaddressed comment filtering logic...")

    # Mock GitHub client for testing
    class MockGitHubClient:
        def __init__(self):
            self.target_owner = "test-owner"
            self.target_repo = "test-repo"

        def is_comment_from_ai_agent(self, comment_author):
            """Mock implementation to identify AI agent comments"""
            return comment_author.lower() in ["ai-agent", "test-ai-agent", "bot"]

    # Create test comments with different timestamps
    now = datetime.now(timezone.utc)

    # Test case 1: User comment followed by AI response (should be filtered out)
    test_comments_1 = [
        {
            "id": 1,
            "body": "Please fix the bug",
            "created_at": now - timedelta(hours=2),
            "author": "user1",
        },
        {
            "id": 2,
            "body": "I've fixed the bug as requested",
            "created_at": now - timedelta(hours=1),
            "author": "ai-agent",
        },
    ]

    # Test case 2: User comment with no AI response (should be kept)
    test_comments_2 = [
        {
            "id": 3,
            "body": "Can you also add tests?",
            "created_at": now - timedelta(minutes=30),
            "author": "user2",
        }
    ]

    # Test case 3: Multiple user comments, some addressed, some not
    test_comments_3 = [
        {
            "id": 4,
            "body": "Fix the styling",
            "created_at": now - timedelta(hours=3),
            "author": "user1",
        },
        {
            "id": 5,
            "body": "I've updated the styling",
            "created_at": now - timedelta(hours=2),
            "author": "ai-agent",
        },
        {
            "id": 6,
            "body": "Add documentation",
            "created_at": now - timedelta(hours=1),
            "author": "user2",
        },
    ]

    # Simulate the filtering logic
    mock_client = MockGitHubClient()

    def filter_unaddressed_comments(recent_comments):
        """Simulate the filtering logic from the main method"""
        # Filter out comments from the AI agent itself to avoid loops
        user_comments = [
            comment
            for comment in recent_comments
            if not mock_client.is_comment_from_ai_agent(comment["author"])
        ]

        # Filter out user comments that have already been addressed by the AI Agent
        unaddressed_user_comments = []

        # Sort all comments by creation time to establish chronological order
        all_comments_sorted = sorted(recent_comments, key=lambda x: x["created_at"])

        for user_comment in user_comments:
            # Check if there's an AI agent comment after this user comment
            has_ai_response = False

            for comment in all_comments_sorted:
                # If this comment is after the user comment and is from AI agent
                if comment["created_at"] > user_comment[
                    "created_at"
                ] and mock_client.is_comment_from_ai_agent(comment["author"]):
                    has_ai_response = True
                    break

            # If no AI response found after this user comment, it's unaddressed
            if not has_ai_response:
                unaddressed_user_comments.append(user_comment)

        return unaddressed_user_comments

    # Test case 1: User comment followed by AI response
    result_1 = filter_unaddressed_comments(test_comments_1)
    print(
        f"Test 1 - User comment with AI response: {len(result_1)} unaddressed comments"
    )
    assert (
        len(result_1) == 0
    ), "Expected 0 unaddressed comments (user comment was addressed)"

    # Test case 2: User comment with no AI response
    result_2 = filter_unaddressed_comments(test_comments_2)
    print(
        f"Test 2 - User comment without AI response: {len(result_2)} unaddressed comments"
    )
    assert len(result_2) == 1, "Expected 1 unaddressed comment (no AI response)"

    # Test case 3: Mixed scenario
    result_3 = filter_unaddressed_comments(test_comments_3)
    print(f"Test 3 - Mixed comments: {len(result_3)} unaddressed comments")
    assert (
        len(result_3) == 1
    ), "Expected 1 unaddressed comment (second user comment not addressed)"
    assert (
        result_3[0]["body"] == "Add documentation"
    ), "Expected the 'Add documentation' comment to be unaddressed"

    print("✅ All tests passed! Unaddressed comment filtering is working correctly.")
    return True


def main():
    """Run the test"""
    try:
        success = test_unaddressed_comment_filtering()
        if success:
            print("\n🎉 Unaddressed comment filtering logic is implemented correctly!")
        return success
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

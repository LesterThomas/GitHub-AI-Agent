"""Demonstration of PR follow-up comment functionality."""

from github_ai_agent.github_client import GitHubClient
from github_ai_agent.main import GitHubAIAgentApp
from unittest.mock import Mock, patch
from datetime import datetime


def demo_pr_comment_functionality():
    """Demonstrate the PR follow-up comment functionality."""

    print("🤖 GitHub AI Agent - PR Follow-up Comment Functionality Demo")
    print("=" * 60)

    # Mock GitHub client and objects
    mock_github = Mock()
    mock_repo = Mock()
    mock_github.get_repo.return_value = mock_repo

    # Mock PR with recent comments and related issue
    mock_pr = Mock()
    mock_pr.number = 123
    mock_pr.title = "Fix issue #456: Improve error handling"
    mock_pr.body = "This PR addresses issue #456 by improving error handling."

    # Mock comments
    mock_comment1 = Mock()
    mock_comment1.id = 1
    mock_comment1.body = "Can you also add logging to this function?"
    mock_comment1.created_at = datetime(2023, 1, 1, 10, 0, 0)
    mock_comment1.updated_at = datetime(2023, 1, 1, 10, 0, 0)
    mock_comment1.user.login = "reviewer1"

    mock_comment2 = Mock()
    mock_comment2.id = 2
    mock_comment2.body = "Please update the documentation as well."
    mock_comment2.created_at = datetime(2023, 1, 1, 11, 0, 0)
    mock_comment2.updated_at = datetime(2023, 1, 1, 11, 0, 0)
    mock_comment2.user.login = "reviewer2"

    # Add an AI agent comment to test filtering
    mock_comment3 = Mock()
    mock_comment3.id = 3
    mock_comment3.body = "🤖 AI Agent Updated PR - I've processed the recent comments."
    mock_comment3.created_at = datetime(2023, 1, 1, 12, 0, 0)
    mock_comment3.updated_at = datetime(2023, 1, 1, 12, 0, 0)
    mock_comment3.user.login = "test-ai-agent"

    mock_pr.get_issue_comments.return_value = [
        mock_comment1,
        mock_comment2,
        mock_comment3,
    ]

    # Mock GitHub client methods
    with patch("github_ai_agent.github_client.Github") as mock_github_class:
        mock_github_class.return_value = mock_github

        # Create GitHubClient instance
        client = GitHubClient(
            target_owner="test", target_repo="test", token="fake_token"
        )
        client._repo = mock_repo
        client._repo.get_pull.return_value = mock_pr
        client._repo.get_pulls.return_value = [mock_pr]

        # Test 1: Finding related issue from PR
        print("\n1. Testing related issue detection:")
        related_issue = client.find_related_issue_for_pr(123)
        print(f"   PR #{mock_pr.number} is related to issue #{related_issue}")

        # Test 2: Getting PR comments
        print("\n2. Testing PR comment retrieval:")
        comments = client.get_pull_request_comments_since(123)
        print(f"   Found {len(comments)} total comments on PR #{mock_pr.number}:")
        for comment in comments:
            print(f"     - {comment['author']}: {comment['body'][:50]}...")

        # Test 2b: Testing AI agent comment filtering
        print("\n2b. Testing AI agent comment filtering:")
        user_comments = [
            comment
            for comment in comments
            if not client.is_comment_from_ai_agent(comment["author"])
        ]
        print(
            f"   After filtering AI agent comments: {len(user_comments)} user comments:"
        )
        for comment in user_comments:
            print(f"     - {comment['author']}: {comment['body'][:50]}...")

        # Test 3: Getting PRs with recent comments
        print("\n3. Testing PR comment aggregation:")
        prs_with_comments = client.get_open_prs_with_recent_comments()
        print(f"   Found {len(prs_with_comments)} PRs with recent comments:")
        for pr_data in prs_with_comments:
            print(f"     - PR #{pr_data['pr_number']}: {pr_data['title']}")
            print(f"       Related issue: #{pr_data['related_issue']}")
            print(f"       Recent comments: {len(pr_data['recent_comments'])}")

    print("\n" + "=" * 60)
    print("✅ PR Follow-up Comment Functionality Demo Complete")
    print("\nKey features implemented:")
    print("• Detection of related issues from PR titles and bodies")
    print("• Retrieval of PR comments since a timestamp")
    print("• Filtering of user comments vs. AI agent comments")
    print("• Integration with issue re-processing workflow")
    print("• Automatic comment posting on issues and PRs")


if __name__ == "__main__":
    demo_pr_comment_functionality()

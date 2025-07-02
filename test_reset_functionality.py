#!/usr/bin/env python3
"""Test the new GitHub client methods for closing issues/PRs and creating issues."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.github_client import GitHubClient


def test_close_issue():
    """Test that close_issue method works correctly."""
    print("Testing close_issue method...")
    
    with patch("github_ai_agent.github_client.Github") as mock_github:
        # Mock the GitHub API
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.edit = Mock()
        mock_repo.get_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient("test_token", "test_owner", "test_repo")
        result = client.close_issue(123)

        # Verify the issue was closed
        assert result is True
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.edit.assert_called_once_with(state="closed")
        print("✅ close_issue test passed")


def test_get_pull_requests():
    """Test that get_pull_requests method works correctly."""
    print("Testing get_pull_requests method...")
    
    with patch("github_ai_agent.github_client.Github") as mock_github:
        # Mock the GitHub API
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_repo.get_pulls.return_value = [mock_pr]
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient("test_token", "test_owner", "test_repo")
        prs = client.get_pull_requests("open")

        assert len(prs) == 1
        assert prs[0].number == 1
        assert prs[0].title == "Test PR"
        mock_repo.get_pulls.assert_called_once_with(state="open")
        print("✅ get_pull_requests test passed")


def test_close_pull_request():
    """Test that close_pull_request method works correctly."""
    print("Testing close_pull_request method...")
    
    with patch("github_ai_agent.github_client.Github") as mock_github:
        # Mock the GitHub API
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.edit = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient("test_token", "test_owner", "test_repo")
        result = client.close_pull_request(123)

        # Verify the PR was closed
        assert result is True
        mock_repo.get_pull.assert_called_once_with(123)
        mock_pr.edit.assert_called_once_with(state="closed")
        print("✅ close_pull_request test passed")


def test_create_issue():
    """Test that create_issue method works correctly."""
    print("Testing create_issue method...")
    
    with patch("github_ai_agent.github_client.Github") as mock_github:
        # Mock the GitHub API
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 42
        mock_issue.title = "Test Issue"
        mock_repo.create_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient("test_token", "test_owner", "test_repo")
        issue = client.create_issue("Test Issue", "Test body", ["test-label"])

        assert issue is not None
        assert issue.number == 42
        assert issue.title == "Test Issue"
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue", body="Test body", labels=["test-label"]
        )
        print("✅ create_issue test passed")


def main():
    """Run all tests."""
    print("🧪 Running tests for new GitHubClient methods...\n")
    
    try:
        test_close_issue()
        test_get_pull_requests()
        test_close_pull_request()
        test_create_issue()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
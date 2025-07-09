"""Test PR follow-up comment functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from github_ai_agent.github_client import GitHubClient


class TestPRComments:
    """Test PR comment functionality."""

    def test_find_related_issue_for_pr_from_body(self):
        """Test finding related issue from PR body."""

        # Mock GitHub client with a PR that has issue reference in body
        mock_pr = Mock()
        mock_pr.body = "This PR fixes issue #123 and resolves the problem."
        mock_pr.title = "Fix some bug"

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr

        # Create a mock GitHub client
        with patch("github_ai_agent.github_client.Github") as mock_github:
            mock_github.return_value.get_repo.return_value = mock_repo

            client = GitHubClient(
                target_owner="test", target_repo="test", token="fake_token"
            )
            client.repo = mock_repo

            # Test finding related issue
            result = client.find_related_issue_for_pr(456)

            assert result == 123
            mock_repo.get_pull.assert_called_once_with(456)

    def test_find_related_issue_for_pr_from_title(self):
        """Test finding related issue from PR title."""

        # Mock GitHub client with a PR that has issue reference in title
        mock_pr = Mock()
        mock_pr.body = "Some description without issue reference"
        mock_pr.title = "Processing Issue #789: Fix the bug"

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr

        # Create a mock GitHub client
        with patch("github_ai_agent.github_client.Github") as mock_github:
            mock_github.return_value.get_repo.return_value = mock_repo

            client = GitHubClient(
                target_owner="test", target_repo="test", token="fake_token"
            )
            client.repo = mock_repo

            # Test finding related issue
            result = client.find_related_issue_for_pr(456)

            assert result == 789
            mock_repo.get_pull.assert_called_once_with(456)

    def test_find_related_issue_for_pr_no_reference(self):
        """Test when PR has no issue reference."""

        # Mock GitHub client with a PR that has no issue reference
        mock_pr = Mock()
        mock_pr.body = "Some description without issue reference"
        mock_pr.title = "Fix some bug"

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr

        # Create a mock GitHub client
        with patch("github_ai_agent.github_client.Github") as mock_github:
            mock_github.return_value.get_repo.return_value = mock_repo

            client = GitHubClient(
                target_owner="test", target_repo="test", token="fake_token"
            )
            client.repo = mock_repo

            # Test finding related issue
            result = client.find_related_issue_for_pr(456)

            assert result is None
            mock_repo.get_pull.assert_called_once_with(456)

    def test_get_pull_request_comments_since(self):
        """Test getting PR comments since a timestamp."""

        # Mock comment objects
        mock_comment1 = Mock()
        mock_comment1.id = 1
        mock_comment1.body = "First comment"
        mock_comment1.created_at = datetime(2023, 1, 1, 10, 0, 0)
        mock_comment1.updated_at = datetime(2023, 1, 1, 10, 0, 0)
        mock_comment1.user.login = "user1"

        mock_comment2 = Mock()
        mock_comment2.id = 2
        mock_comment2.body = "Second comment"
        mock_comment2.created_at = datetime(2023, 1, 1, 11, 0, 0)
        mock_comment2.updated_at = datetime(2023, 1, 1, 11, 0, 0)
        mock_comment2.user.login = "user2"

        # Mock PR with comments
        mock_pr = Mock()
        mock_pr.get_issue_comments.return_value = [mock_comment1, mock_comment2]

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr

        # Create a mock GitHub client
        with patch("github_ai_agent.github_client.Github") as mock_github:
            mock_github.return_value.get_repo.return_value = mock_repo

            client = GitHubClient(
                target_owner="test", target_repo="test", token="fake_token"
            )
            client.repo = mock_repo

            # Test getting all comments (no since filter)
            result = client.get_pull_request_comments_since(123)

            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[0]["body"] == "First comment"
            assert result[0]["author"] == "user1"
            assert result[1]["id"] == 2
            assert result[1]["body"] == "Second comment"
            assert result[1]["author"] == "user2"

    def test_get_open_prs_with_recent_comments(self):
        """Test getting open PRs with recent comments."""

        # Mock PR
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.body = "This PR fixes issue #456"

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pr]

        # Create a mock GitHub client
        with patch("github_ai_agent.github_client.Github") as mock_github:
            mock_github.return_value.get_repo.return_value = mock_repo

            client = GitHubClient(
                target_owner="test", target_repo="test", token="fake_token"
            )
            client.repo = mock_repo

            # Mock the other methods
            with patch.object(
                client, "get_pull_request_comments_since"
            ) as mock_get_comments:
                with patch.object(
                    client, "find_related_issue_for_pr"
                ) as mock_find_issue:
                    # Setup mock returns
                    mock_get_comments.return_value = [
                        {"id": 1, "body": "Test comment", "author": "user1"}
                    ]
                    mock_find_issue.return_value = 456

                    # Test getting PRs with recent comments
                    result = client.get_open_prs_with_recent_comments()

                    assert len(result) == 1
                    assert result[0]["pr_number"] == 123
                    assert result[0]["title"] == "Test PR"
                    assert result[0]["related_issue"] == 456
                    assert len(result[0]["recent_comments"]) == 1

                    mock_get_comments.assert_called_once_with(123, None)
                    mock_find_issue.assert_called_once_with(123)

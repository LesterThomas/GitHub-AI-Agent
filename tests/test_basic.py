"""Basic tests for the GitHub AI Agent."""

from unittest.mock import Mock, patch

import pytest

from github_ai_agent.config import Settings
from github_ai_agent.github_client import GitHubClient


def test_settings_creation():
    """Test that settings can be created with required fields."""
    with patch.dict(
        "os.environ",
        {"GITHUB_TOKEN": "test_token", "OPENAI_API_KEY": "test_openai_key"},
    ):
        settings = Settings()
        assert settings.github_token == "test_token"
        assert settings.openai_api_key == "test_openai_key"
        assert settings.target_owner == "LesterThomas"
        assert settings.target_repo == "SAAA"
        assert settings.issue_assignee == "Test-AI-Agent"


def test_github_client_initialization():
    """Test that GitHub client can be initialized."""
    client = GitHubClient(
        token="test_token", target_owner="test_owner", target_repo="test_repo"
    )
    assert client.target_owner == "test_owner"
    assert client.target_repo == "test_repo"


@patch("github_ai_agent.github_client.Github")
def test_github_client_get_issues(mock_github):
    """Test getting issues with label."""
    # Mock the GitHub API
    mock_repo = Mock()
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_repo.get_issues.return_value = [mock_issue]
    mock_github.return_value.get_repo.return_value = mock_repo

    client = GitHubClient("test_token", "test_owner", "test_repo")
    issues = client.get_issues_with_label("test_label")

    assert len(issues) == 1
    assert issues[0].number == 1
    assert issues[0].title == "Test Issue"
    mock_repo.get_issues.assert_called_once_with(state="open", labels=["test_label"])


@patch("github_ai_agent.github_client.Github")
def test_github_client_get_issues_assigned_to(mock_github):
    """Test getting issues assigned to a specific user."""
    # Mock the GitHub API
    mock_repo = Mock()
    mock_issue = Mock()
    mock_issue.number = 2
    mock_issue.title = "Assigned Issue"
    mock_repo.get_issues.return_value = [mock_issue]
    mock_github.return_value.get_repo.return_value = mock_repo

    client = GitHubClient("test_token", "test_owner", "test_repo")
    issues = client.get_issues_assigned_to("Test-AI-Agent")

    assert len(issues) == 1
    assert issues[0].number == 2
    assert issues[0].title == "Assigned Issue"
    mock_repo.get_issues.assert_called_once_with(state="open", assignee="Test-AI-Agent")


@patch("github_ai_agent.github_client.Github")
def test_github_client_close_issue(mock_github):
    """Test closing an issue."""
    # Mock the GitHub API
    mock_repo = Mock()
    mock_issue = Mock()
    mock_issue.edit = Mock()
    mock_repo.get_issue.return_value = mock_issue
    mock_github.return_value.get_repo.return_value = mock_repo

    client = GitHubClient("test_token", "test_owner", "test_repo")
    result = client.close_issue(123)

    assert result is True
    mock_repo.get_issue.assert_called_once_with(123)
    mock_issue.edit.assert_called_once_with(state="closed")


@patch("github_ai_agent.github_client.Github")
def test_github_client_get_pull_requests(mock_github):
    """Test getting pull requests."""
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


@patch("github_ai_agent.github_client.Github")
def test_github_client_close_pull_request(mock_github):
    """Test closing a pull request."""
    # Mock the GitHub API
    mock_repo = Mock()
    mock_pr = Mock()
    mock_pr.edit = Mock()
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo

    client = GitHubClient("test_token", "test_owner", "test_repo")
    result = client.close_pull_request(123)

    assert result is True
    mock_repo.get_pull.assert_called_once_with(123)
    mock_pr.edit.assert_called_once_with(state="closed")


@patch("github_ai_agent.github_client.Github")
def test_github_client_create_issue(mock_github):
    """Test creating an issue."""
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


if __name__ == "__main__":
    pytest.main([__file__])

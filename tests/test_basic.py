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
        assert settings.issue_label == "AI Agent"


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


if __name__ == "__main__":
    pytest.main([__file__])

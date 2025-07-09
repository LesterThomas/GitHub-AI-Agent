"""Test the AI agent comment filtering functionality."""

from github_ai_agent.github_client import GitHubClient
from unittest.mock import Mock, patch


def test_ai_agent_comment_filtering():
    """Test that AI agent comments are properly filtered."""

    print("Testing AI Agent Comment Filtering")
    print("=" * 40)

    # Create a mock GitHub client
    with patch("github_ai_agent.github_client.Github") as mock_github:
        mock_github.return_value.get_repo.return_value = Mock()

        client = GitHubClient(
            target_owner="test", target_repo="test", token="fake_token"
        )

        # Test cases for AI agent detection
        test_cases = [
            ("test-ai-agent", True, "AI agent username"),
            ("ai-agent-bot", True, "AI agent with bot suffix"),
            ("github-actions[bot]", True, "GitHub Actions bot"),
            ("dependabot[bot]", True, "Dependabot"),
            ("regular-user", False, "Regular user"),
            ("user-with-bot-in-name", True, "User with 'bot' in name"),
            ("AI-AGENT", True, "Uppercase AI agent"),
            ("normaluser", False, "Normal user"),
        ]

        print("Testing comment author detection:")
        for username, expected, description in test_cases:
            result = client.is_comment_from_ai_agent(username)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"  {status} {username} -> {result} ({description})")

        print("\n" + "=" * 40)
        print("✅ AI Agent Comment Filtering Test Complete")


if __name__ == "__main__":
    test_ai_agent_comment_filtering()

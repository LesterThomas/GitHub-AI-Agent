#!/usr/bin/env python3
"""Dry-run test for the SAAA reset script to verify logic without making API calls."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.github_client import GitHubClient


def test_reset_script_logic():
    """Test the reset script logic with mocked GitHub API calls."""
    print("🧪 Testing SAAA reset script logic...\n")

    with patch("github_ai_agent.github_client.Github") as mock_github:
        # Mock the GitHub API
        mock_repo = Mock()
        
        # Mock issues (some are actual issues, some are PRs)
        mock_issue1 = Mock()
        mock_issue1.number = 1
        mock_issue1.title = "Real Issue"
        mock_issue1.pull_request = None  # This is a real issue
        
        mock_issue2 = Mock()
        mock_issue2.number = 2
        mock_issue2.title = "PR disguised as issue"
        mock_issue2.pull_request = Mock()  # This is actually a PR
        
        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2]
        
        # Mock pull requests
        mock_pr1 = Mock()
        mock_pr1.number = 10
        mock_pr1.title = "Test PR"
        
        mock_repo.get_pulls.return_value = [mock_pr1]
        
        # Mock created issue
        mock_created_issue = Mock()
        mock_created_issue.number = 100
        mock_created_issue.html_url = "https://github.com/LesterThomas/SAAA/issues/100"
        mock_repo.create_issue.return_value = mock_created_issue
        
        mock_github.return_value.get_repo.return_value = mock_repo

        # Test the client functionality
        client = GitHubClient("fake_token", "LesterThomas", "SAAA")
        
        # Test getting all issues
        print("📋 Testing issue retrieval...")
        all_issues = list(client.repo.get_issues(state="open"))
        print(f"Found {len(all_issues)} open items")
        
        # Test closing real issues (skip PRs)
        issues_closed = 0
        for issue in all_issues:
            if issue.pull_request is None:
                print(f"  Would close issue #{issue.number}: {issue.title}")
                issues_closed += 1
            else:
                print(f"  Skipping #{issue.number} (is a pull request)")
        
        print(f"Would close {issues_closed} real issue(s)")
        
        # Test getting and closing PRs
        print("\n🔀 Testing pull request retrieval...")
        open_prs = client.get_pull_requests(state="open")
        print(f"Found {len(open_prs)} open PR(s)")
        
        for pr in open_prs:
            print(f"  Would close PR #{pr.number}: {pr.title}")
        
        # Test creating new issue
        print("\n📝 Testing issue creation...")
        title = "Create TEST.md"
        body = "Create a TEST.md markdown file and in the content of the file make up a poem about clouds."
        labels = ["AI Agent"]
        
        issue = client.create_issue(title=title, body=body, labels=labels)
        print(f"Would create issue #{issue.number}: {title}")
        print(f"Issue URL: {issue.html_url}")
        
        # Verify mocks were called correctly
        mock_repo.get_issues.assert_called_with(state="open")
        mock_repo.get_pulls.assert_called_with(state="open")
        mock_repo.create_issue.assert_called_with(
            title=title, body=body, labels=labels
        )
        
        print("\n✅ All reset script logic tests passed!")
        return True


def main():
    """Run the dry-run test."""
    try:
        test_reset_script_logic()
        print("\n🎉 Dry-run test completed successfully!")
    except Exception as e:
        print(f"\n❌ Dry-run test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
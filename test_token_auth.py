#!/usr/bin/env python3
"""Test script for token authentication."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.config import get_settings
from github_ai_agent.github_client import GitHubClient


def test_token_auth():
    """Test GitHub token authentication."""
    print("Testing GitHub token authentication...")

    # Load settings
    settings = get_settings()

    print(
        f"GitHub Token: {settings.github_token[:10]}..."
        if settings.github_token
        else "None"
    )
    print(f"Target repo: {settings.target_owner}/{settings.target_repo}")

    try:
        # Initialize GitHub client with token authentication
        if settings.github_token:
            client = GitHubClient(
                target_owner=settings.target_owner,
                target_repo=settings.target_repo,
                token=settings.github_token,
            )
            print("✅ GitHub client initialized successfully with token authentication")

            # Test basic API call
            try:
                repo = client.repo
                print(f"✅ Successfully accessed repository: {repo.full_name}")
                print(f"Repository description: {repo.description}")
                print(f"Repository default branch: {repo.default_branch}")

                # Test issue fetching
                issues = client.get_issues_with_label(settings.issue_label)
                print(
                    f"✅ Found {len(issues)} issues with label '{settings.issue_label}'"
                )
                return True
            except Exception as e:
                print(f"❌ Failed to access repository: {e}")
                return False

        else:
            print("❌ GitHub token not found in .env file")
            return False

    except Exception as e:
        print(f"❌ Failed to initialize GitHub client: {e}")
        return False


if __name__ == "__main__":
    success = test_token_auth()
    sys.exit(0 if success else 1)

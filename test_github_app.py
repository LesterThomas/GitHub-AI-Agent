#!/usr/bin/env python3
"""Test script for GitHub App authentication."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.config import get_settings
from github_ai_agent.github_client import GitHubClient


def test_github_app_auth():
    """Test GitHub App authentication."""
    print("Testing GitHub App authentication...")

    # Load settings
    settings = get_settings()

    print(f"GitHub App ID: {settings.github_app_id}")
    print(f"GitHub Client ID: {settings.github_client_id}")
    print(f"Target repo: {settings.target_owner}/{settings.target_repo}")

    # Check if client_secret looks like a PAT
    if settings.github_client_secret:
        if settings.github_client_secret.startswith(
            "ghp_"
        ) or settings.github_client_secret.startswith("github_pat_"):
            print("✅ Client secret appears to be a Personal Access Token")
        else:
            print(
                "ℹ️ Client secret does not appear to be a PAT (might need device flow)"
            )

    try:
        # Initialize GitHub client with App authentication
        if (
            settings.github_app_id
            and settings.github_client_id
            and settings.github_client_secret
        ):
            client = GitHubClient(
                target_owner=settings.target_owner,
                target_repo=settings.target_repo,
                app_id=settings.github_app_id,
                client_id=settings.github_client_id,
                client_secret=settings.github_client_secret,
            )
            print("✅ GitHub client initialized successfully with App authentication")

            # Test basic API call
            try:
                repo = client.repo
                print(f"✅ Successfully accessed repository: {repo.full_name}")
                print(f"Repository description: {repo.description}")
                print(f"Repository default branch: {repo.default_branch}")
                return True
            except Exception as e:
                print(f"❌ Failed to access repository: {e}")
                return False

        else:
            print("❌ GitHub App credentials not found in .env file")
            return False

    except Exception as e:
        print(f"❌ Failed to initialize GitHub client: {e}")
        return False


if __name__ == "__main__":
    success = test_github_app_auth()
    sys.exit(0 if success else 1)

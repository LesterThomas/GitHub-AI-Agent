#!/usr/bin/env python3
"""Test the GitHub App authentication to make sure we have working credentials."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from github_ai_agent.github_client import GitHubClient

# Load environment variables from .env file
load_dotenv()


def test_github_app_auth():
    """Test GitHub App authentication."""
    print("🧪 Testing GitHub App Authentication")
    print("=" * 40)

    # Get configuration from environment variables
    target_owner = os.getenv("TARGET_OWNER", "LesterThomas")
    target_repo = os.getenv("TARGET_REPO", "SAAA")

    # Get GitHub App credentials
    github_app_id = os.getenv("GITHUB_APP_ID")
    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")

    print(f"Target repository: {target_owner}/{target_repo}")
    print(f"GitHub App ID: {github_app_id}")
    print()

    # Initialize GitHub client using GitHub App authentication
    try:
        client = GitHubClient(
            target_owner=target_owner,
            target_repo=target_repo,
            app_id=github_app_id,
            client_id=github_client_id,
            client_secret=github_client_secret,
            prefer_token=False,  # Force GitHub App authentication
        )
        print(
            "✅ GitHub client initialized successfully with GitHub App authentication"
        )
    except Exception as e:
        print(f"❌ Failed to initialize GitHub client: {e}")
        return

    # Test repository access
    print("\n📁 Testing repository access")
    print("-" * 30)
    try:
        repo = client.repo
        print(f"✅ Successfully accessed repository: {repo.full_name}")
        print(f"   Repository description: {repo.description}")
        print(f"✅ GitHub App authentication working correctly")

    except Exception as e:
        print(f"❌ Failed to access repository: {e}")
        return

    # Test listing issues
    print("\n📋 Testing issue access")
    print("-" * 30)
    try:
        issues = list(client.repo.get_issues(state="open"))
        print(f"✅ Successfully retrieved {len(issues)} open issues")

    except Exception as e:
        print(f"❌ Failed to access issues: {e}")

    print("\n🎉 GitHub App authentication test completed!")


if __name__ == "__main__":
    test_github_app_auth()

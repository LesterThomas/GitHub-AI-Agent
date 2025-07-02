#!/usr/bin/env python3
"""Test script for GitHub App authentication with private key."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.config import get_settings
from github_ai_agent.github_client import GitHubClient


def test_github_app_auth():
    """Test GitHub App authentication with private key."""
    print("Testing GitHub App authentication with private key...")
    print("=" * 60)

    # Load settings
    settings = get_settings()

    print(f"GitHub App ID: {settings.github_app_id}")
    print(f"GitHub Client ID: {settings.github_client_id}")
    print(f"Target repo: {settings.target_owner}/{settings.target_repo}")
    print(f"Private key file: ea-agent.2025-07-02.private-key.pem")
    print()

    try:
        # Initialize GitHub client with App authentication
        if (
            settings.github_app_id
            and settings.github_client_id
            and settings.github_client_secret
        ):
            print("🔄 Initializing GitHub App client...")
            client = GitHubClient(
                target_owner=settings.target_owner,
                target_repo=settings.target_repo,
                app_id=settings.github_app_id,
                client_id=settings.github_client_id,
                client_secret=settings.github_client_secret,
                private_key_path="ea-agent.2025-07-02.private-key.pem",
            )
            print("✅ GitHub client initialized successfully with App authentication")

            # Test basic API call
            try:
                print("🔄 Testing repository access...")
                repo = client.repo
                print(f"✅ Successfully accessed repository: {repo.full_name}")
                print(f"   Repository description: {repo.description}")
                print(f"   Repository default branch: {repo.default_branch}")
                print(f"   Repository owner: {repo.owner.login}")

                # Test issue fetching
                print("🔄 Testing issue fetching...")
                issues = client.get_issues_with_label(settings.issue_label)
                print(
                    f"✅ Found {len(issues)} issues with label '{settings.issue_label}'"
                )

                if issues:
                    for issue in issues[:3]:  # Show first 3 issues
                        print(f"   - Issue #{issue.number}: {issue.title}")

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
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: GitHub App authentication is working!")
        print("Your AI Agent is now configured to use the EA Agent GitHub App")
    else:
        print("❌ FAILED: GitHub App authentication needs attention")
    print("=" * 60)
    sys.exit(0 if success else 1)

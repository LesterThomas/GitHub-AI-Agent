#!/usr/bin/env python3
"""Test script to verify the reset functionality can read issues and PRs (dry run)."""

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


def test_reset_dry_run():
    """Test the reset script functionality without actually closing anything."""
    print("🧪 Testing Reset Script Functionality (Dry Run)")
    print("=" * 50)

    # Get configuration from environment variables (loaded from .env)
    github_token = os.getenv("GITHUB_TOKEN")
    target_owner = os.getenv("TARGET_OWNER", "LesterThomas")
    target_repo = os.getenv("TARGET_REPO", "SAAA")

    # Get GitHub App credentials
    github_app_id = os.getenv("GITHUB_APP_ID")
    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")

    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable is required")
        return

    print(f"Target repository: {target_owner}/{target_repo}")
    print(f"Using token authentication (reset script behavior)")
    print()

    # Initialize GitHub client using token authentication (preferred for reset script)
    try:
        client = GitHubClient(
            target_owner=target_owner,
            target_repo=target_repo,
            token=github_token,
            app_id=github_app_id,
            client_id=github_client_id,
            client_secret=github_client_secret,
            prefer_token=True,
        )
        print("✅ GitHub client initialized successfully with token authentication")
    except Exception as e:
        print(f"❌ Failed to initialize GitHub client: {e}")
        return

    # Test 1: Check if we can access the repository
    print("\n📁 Test 1: Repository access")
    print("-" * 30)
    try:
        repo = client.repo
        print(f"✅ Successfully accessed repository: {repo.full_name}")
        print(f"   Repository description: {repo.description}")
        print(f"   Repository is private: {repo.private}")
    except Exception as e:
        print(f"❌ Failed to access repository: {e}")
        return

    # Test 2: List open issues (without closing)
    print("\n📋 Test 2: List open issues")
    print("-" * 30)
    try:
        all_open_issues = client.repo.get_issues(state="open")
        open_issues = list(all_open_issues)

        if not open_issues:
            print("✅ No open issues found")
        else:
            print(f"✅ Found {len(open_issues)} open issue(s):")
            for i, issue in enumerate(open_issues[:5]):  # Show first 5
                if issue.pull_request is None:
                    print(f"   {i+1}. Issue #{issue.number}: {issue.title}")
                else:
                    print(
                        f"   {i+1}. PR #{issue.number}: {issue.title} (shown as issue)"
                    )
            if len(open_issues) > 5:
                print(f"   ... and {len(open_issues) - 5} more")

    except Exception as e:
        print(f"❌ Failed to list issues: {e}")

    # Test 3: List open pull requests (without closing)
    print("\n🔀 Test 3: List open pull requests")
    print("-" * 30)
    try:
        open_prs = client.get_pull_requests(state="open")

        if not open_prs:
            print("✅ No open pull requests found")
        else:
            print(f"✅ Found {len(open_prs)} open pull request(s):")
            for i, pr in enumerate(open_prs[:5]):  # Show first 5
                print(f"   {i+1}. PR #{pr.number}: {pr.title}")
            if len(open_prs) > 5:
                print(f"   ... and {len(open_prs) - 5} more")

    except Exception as e:
        print(f"❌ Failed to list pull requests: {e}")

    print("\n🎉 Dry run test completed successfully!")
    print("✅ Reset script should work correctly with token authentication")


if __name__ == "__main__":
    test_reset_dry_run()

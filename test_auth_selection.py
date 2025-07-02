#!/usr/bin/env python3
"""Test script to verify authentication method selection in GitHubClient."""

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


def test_authentication_selection():
    """Test authentication method selection logic."""
    print("🧪 Testing GitHub Client Authentication Selection")
    print("=" * 50)

    # Get credentials from environment
    github_token = os.getenv("GITHUB_TOKEN")
    github_app_id = os.getenv("GITHUB_APP_ID")
    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    target_owner = os.getenv("TARGET_OWNER", "LesterThomas")
    target_repo = os.getenv("TARGET_REPO", "SAAA")

    print(f"Available credentials:")
    print(f"  GitHub Token: {'✅' if github_token else '❌'}")
    print(f"  GitHub App ID: {'✅' if github_app_id else '❌'}")
    print(f"  GitHub Client ID: {'✅' if github_client_id else '❌'}")
    print(f"  GitHub Client Secret: {'✅' if github_client_secret else '❌'}")
    print()

    # Test 1: prefer_token=True (reset script behavior)
    print("Test 1: prefer_token=True (reset script behavior)")
    print("-" * 40)
    try:
        client1 = GitHubClient(
            target_owner=target_owner,
            target_repo=target_repo,
            token=github_token,
            app_id=github_app_id,
            client_id=github_client_id,
            client_secret=github_client_secret,
            prefer_token=True,
        )

        # Test basic functionality
        user = client1.github.get_user()
        print(f"✅ Successfully authenticated as: {user.login}")
        print(f"   Authentication method: Token preferred")

    except Exception as e:
        print(f"❌ Failed: {e}")

    print()

    # Test 2: prefer_token=False (main app behavior)
    print("Test 2: prefer_token=False (main app behavior)")
    print("-" * 40)
    try:
        client2 = GitHubClient(
            target_owner=target_owner,
            target_repo=target_repo,
            token=github_token,
            app_id=github_app_id,
            client_id=github_client_id,
            client_secret=github_client_secret,
            prefer_token=False,
        )

        # Test basic functionality
        user = client2.github.get_user()
        print(f"✅ Successfully authenticated as: {user.login}")
        print(f"   Authentication method: GitHub App preferred")

    except Exception as e:
        print(f"❌ Failed: {e}")

    print()

    # Test 3: Token only
    print("Test 3: Token only authentication")
    print("-" * 40)
    if github_token:
        try:
            client3 = GitHubClient(
                target_owner=target_owner,
                target_repo=target_repo,
                token=github_token,
                prefer_token=True,
            )

            user = client3.github.get_user()
            print(f"✅ Successfully authenticated as: {user.login}")
            print(f"   Authentication method: Token only")

        except Exception as e:
            print(f"❌ Failed: {e}")
    else:
        print("⏭️  Skipped (no token available)")

    print("\n🎉 Authentication selection test completed!")


if __name__ == "__main__":
    test_authentication_selection()

#!/usr/bin/env python3
"""Simple test to verify authentication method selection without API calls."""

import os
import sys
from pathlib import Path
import logging

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Enable debug logging for GitHub client
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()


def test_client_initialization():
    """Test client initialization with different authentication preferences."""
    print("🧪 Testing GitHub Client Initialization")
    print("=" * 45)

    # Get credentials from environment
    github_token = os.getenv("GITHUB_TOKEN")
    github_app_id = os.getenv("GITHUB_APP_ID")
    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    target_owner = os.getenv("TARGET_OWNER", "LesterThomas")
    target_repo = os.getenv("TARGET_REPO", "SAAA")

    print(f"Environment variables loaded:")
    print(f"  GITHUB_TOKEN: {'✅ Set' if github_token else '❌ Not set'}")
    print(f"  GITHUB_APP_ID: {'✅ Set' if github_app_id else '❌ Not set'}")
    print(f"  GITHUB_CLIENT_ID: {'✅ Set' if github_client_id else '❌ Not set'}")
    print(
        f"  GITHUB_CLIENT_SECRET: {'✅ Set' if github_client_secret else '❌ Not set'}"
    )
    print()

    # Import GitHubClient after loading env vars
    from github_ai_agent.github_client import GitHubClient

    # Test 1: Reset script behavior (prefer_token=True)
    print("Test 1: Reset script initialization (prefer_token=True)")
    print("-" * 50)
    try:
        print("Initializing GitHubClient with prefer_token=True...")
        client1 = GitHubClient(
            target_owner=target_owner,
            target_repo=target_repo,
            token=github_token,
            app_id=github_app_id,
            client_id=github_client_id,
            client_secret=github_client_secret,
            prefer_token=True,
        )
        print("✅ Reset script client initialized successfully")
        print(f"   Client type: {type(client1.github)}")

    except Exception as e:
        print(f"❌ Reset script client initialization failed: {e}")

    print()

    # Test 2: Main app behavior (prefer_token=False)
    print("Test 2: Main app initialization (prefer_token=False)")
    print("-" * 50)
    try:
        print("Initializing GitHubClient with prefer_token=False...")
        client2 = GitHubClient(
            target_owner=target_owner,
            target_repo=target_repo,
            token=github_token,
            app_id=github_app_id,
            client_id=github_client_id,
            client_secret=github_client_secret,
            prefer_token=False,
        )
        print("✅ Main app client initialized successfully")
        print(f"   Client type: {type(client2.github)}")

    except Exception as e:
        print(f"❌ Main app client initialization failed: {e}")

    print()
    print("🎉 Client initialization test completed!")


if __name__ == "__main__":
    test_client_initialization()

#!/usr/bin/env python3
"""Test script for main application initialization."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.main import GitHubAIAgentApp


def test_main_app():
    """Test main application initialization."""
    print("Testing main application initialization...")

    try:
        # Initialize the main app
        app = GitHubAIAgentApp()
        print("✅ GitHubAIAgentApp initialized successfully")

        # Test that we can access the GitHub client
        if app.github_client:
            print("✅ GitHub client is available")

            # Test accessing the repository
            try:
                repo = app.github_client.repo
                print(f"✅ Successfully accessed repository: {repo.full_name}")

                # Test polling for issues
                print("Testing issue polling...")
                issues = app.github_client.get_issues_with_label(
                    app.settings.issue_label
                )
                print(
                    f"✅ Found {len(issues)} issues with label '{app.settings.issue_label}'"
                )

                return True
            except Exception as e:
                print(f"❌ Failed to access repository: {e}")
                return False
        else:
            print("❌ GitHub client is not available")
            return False

    except Exception as e:
        print(f"❌ Failed to initialize main app: {e}")
        return False


if __name__ == "__main__":
    success = test_main_app()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)

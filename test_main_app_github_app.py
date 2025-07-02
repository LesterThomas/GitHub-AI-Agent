#!/usr/bin/env python3
"""Test script for main application with GitHub App authentication."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.main import GitHubAIAgentApp


def test_main_app_with_github_app():
    """Test main application with GitHub App authentication."""
    print("Testing main application with GitHub App authentication...")
    print("=" * 70)

    try:
        # Initialize the main app
        print("🔄 Initializing GitHubAIAgentApp...")
        app = GitHubAIAgentApp()
        print("✅ GitHubAIAgentApp initialized successfully")

        # Test that we can access the GitHub client
        if app.github_client:
            print("✅ GitHub client is available")

            # Test accessing the repository
            try:
                print("🔄 Testing repository access...")
                repo = app.github_client.repo
                print(f"✅ Successfully accessed repository: {repo.full_name}")

                # Test polling for issues
                print("🔄 Testing issue polling...")
                issues = app.github_client.get_issues_with_label(
                    app.settings.issue_label
                )
                print(
                    f"✅ Found {len(issues)} issues with label '{app.settings.issue_label}'"
                )

                # Test agent initialization
                if app.agent:
                    print("✅ AI Agent is initialized and ready")
                    print(f"   Model: {app.settings.openai_model}")
                    print(f"   Max iterations: {app.settings.max_iterations}")

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
    success = test_main_app_with_github_app()
    print("\n" + "=" * 70)
    if success:
        print("🎉 SUCCESS: Main application with GitHub App authentication is working!")
        print("Your AI Agent is ready to process issues using the EA Agent GitHub App!")
    else:
        print("❌ FAILED: Main application needs attention")
    print("=" * 70)
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""Test script to reset SAAA repository by closing all open issues and pull requests, then creating a new issue."""

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


def main():
    """Main function to reset the SAAA repository."""
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print("SAAA Repository Reset Script")
        print("=" * 30)
        print("This script will:")
        print("1. Close all open issues in the SAAA repository")
        print("2. Close all open pull requests in the SAAA repository")
        print(
            "3. Create a new issue requesting creation of TEST.md with a poem about clouds"
        )
        print("\nConfiguration:")
        print("- Uses .env file for configuration (create one if it doesn't exist)")
        print("- Required variables: GITHUB_TOKEN, TARGET_OWNER, TARGET_REPO")
        print("- Example .env file:")
        print("  GITHUB_TOKEN=your_github_token_here")
        print("  TARGET_OWNER=LesterThomas")
        print("  TARGET_REPO=SAAA")
        print("\nUsage:")
        print("  python reset_saaa_repo.py")
        return

    # Get configuration from environment variables (loaded from .env)
    github_token = os.getenv("GITHUB_TOKEN")
    target_owner = os.getenv("TARGET_OWNER", "LesterThomas")  # Default fallback
    target_repo = os.getenv("TARGET_REPO", "SAAA")  # Default fallback

    # Get GitHub App credentials (as fallback if token fails)
    github_app_id = os.getenv("GITHUB_APP_ID")
    github_client_id = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")

    if not github_token and not (
        github_app_id and github_client_id and github_client_secret
    ):
        print("Error: Either GITHUB_TOKEN or GitHub App credentials are required")
        print("Create a .env file with GITHUB_TOKEN=your_token")
        print(
            "Or ensure GITHUB_APP_ID, GITHUB_CLIENT_ID, and GITHUB_CLIENT_SECRET are set"
        )
        print("Run 'python reset_saaa_repo.py --help' for more information")
        sys.exit(1)

    # Initialize GitHub client - prefer token if available and valid, fallback to GitHub App
    client = None
    auth_method = "unknown"

    if github_token:
        try:
            print("🔑 Attempting token authentication...")
            client = GitHubClient(
                target_owner=target_owner,
                target_repo=target_repo,
                token=github_token,
                app_id=github_app_id,
                client_id=github_client_id,
                client_secret=github_client_secret,
                prefer_token=True,
            )
            # Test the connection
            _ = client.repo.full_name
            auth_method = "GitHub Token"
            print("✅ Token authentication successful")
        except Exception as e:
            print(f"⚠️ Token authentication failed: {e}")
            client = None

    # Fallback to GitHub App if token failed or not available
    if client is None and github_app_id and github_client_id and github_client_secret:
        try:
            print("🔑 Falling back to GitHub App authentication...")
            client = GitHubClient(
                target_owner=target_owner,
                target_repo=target_repo,
                token=github_token,
                app_id=github_app_id,
                client_id=github_client_id,
                client_secret=github_client_secret,
                prefer_token=False,
            )
            # Test the connection
            _ = client.repo.full_name
            auth_method = "GitHub App"
            print("✅ GitHub App authentication successful")
        except Exception as e:
            print(f"❌ GitHub App authentication also failed: {e}")
            client = None

    if client is None:
        print("❌ Error: Unable to authenticate with GitHub using any available method")
        print("Please check your credentials in the .env file")
        sys.exit(1)

    print("🔄 Starting SAAA repository reset...")
    print(f"📁 Target repository: {target_owner}/{target_repo}")
    print(f"🔐 Authentication method: {auth_method}")

    # Step 1: Get and close all open issues
    print("\n📋 Step 1: Closing all open issues...")
    try:
        # Get all open issues directly from the repo
        all_open_issues = client.repo.get_issues(state="open")
        open_issues = list(all_open_issues)

        if not open_issues:
            print("✅ No open issues found")
        else:
            print(f"🔍 Found {len(open_issues)} open issue(s)")
            for issue in open_issues:
                # Skip pull requests (they appear as issues in GitHub API)
                if issue.pull_request is None:
                    print(f"  🔒 Closing issue #{issue.number}: {issue.title}")
                    if client.close_issue(issue.number):
                        print(f"    ✅ Successfully closed issue #{issue.number}")
                    else:
                        print(f"    ❌ Failed to close issue #{issue.number}")
                else:
                    print(f"  ⏭️  Skipping #{issue.number} (is a pull request)")
    except Exception as e:
        print(f"❌ Error processing issues: {e}")

    # Step 2: Get and close all open pull requests
    print("\n🔀 Step 2: Closing all open pull requests...")
    try:
        open_prs = client.get_pull_requests(state="open")

        if not open_prs:
            print("✅ No open pull requests found")
        else:
            print(f"🔍 Found {len(open_prs)} open pull request(s)")
            for pr in open_prs:
                print(f"  🔒 Closing pull request #{pr.number}: {pr.title}")
                if client.close_pull_request(pr.number):
                    print(f"    ✅ Successfully closed pull request #{pr.number}")
                else:
                    print(f"    ❌ Failed to close pull request #{pr.number}")
    except Exception as e:
        print(f"❌ Error processing pull requests: {e}")

    # Step 3: Create new issue
    print("\n📝 Step 3: Creating new issue...")
    try:
        title = "Create TEST.md"
        body = "Create a TEST.md markdown file and in the content of the file make up a poem about clouds."
        labels = ["AI Agent"]

        issue = client.create_issue(title=title, body=body, labels=labels)
        if issue:
            print(f"✅ Successfully created new issue #{issue.number}: {title}")
            print(f"🔗 Issue URL: {issue.html_url}")
        else:
            print("❌ Failed to create new issue")
    except Exception as e:
        print(f"❌ Error creating new issue: {e}")

    print(f"\n🎉 {target_owner}/{target_repo} repository reset completed!")


if __name__ == "__main__":
    main()

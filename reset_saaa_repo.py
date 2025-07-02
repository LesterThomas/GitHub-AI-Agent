#!/usr/bin/env python3
"""Test script to reset SAAA repository by closing all open issues and pull requests, then creating a new issue."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from github_ai_agent.github_client import GitHubClient


def main():
    """Main function to reset the SAAA repository."""
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print("SAAA Repository Reset Script")
        print("=" * 30)
        print("This script will:")
        print("1. Close all open issues in LesterThomas/SAAA repository")
        print("2. Close all open pull requests in LesterThomas/SAAA repository")
        print("3. Create a new issue requesting creation of TEST.md with a poem about clouds")
        print("\nRequirements:")
        print("- GITHUB_TOKEN environment variable must be set")
        print("- Token must have permissions to read/write issues and pull requests for LesterThomas/SAAA")
        print("\nUsage:")
        print("  python reset_saaa_repo.py")
        print("  GITHUB_TOKEN=your_token python reset_saaa_repo.py")
        return

    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        print("Run 'python reset_saaa_repo.py --help' for more information")
        sys.exit(1)

    # Initialize GitHub client for SAAA repository
    client = GitHubClient(
        token=github_token,
        target_owner="LesterThomas", 
        target_repo="SAAA"
    )

    print("🔄 Starting SAAA repository reset...")
    print(f"📁 Target repository: LesterThomas/SAAA")
    
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

    print("\n🎉 SAAA repository reset completed!")


if __name__ == "__main__":
    main()
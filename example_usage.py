#!/usr/bin/env python3
"""
Example usage of the GitHub AI Agent.

This script demonstrates how to use the agent programmatically.
"""

import os
import sys
from github_ai_agent.config import Settings
from github_ai_agent.github_client import GitHubClient
from github_ai_agent.agent import GitHubIssueAgent


def example_usage():
    """Example usage of the GitHub AI Agent."""

    # Check if required environment variables are set
    required_vars = ["GITHUB_TOKEN", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        print("Please set these variables in your .env file or environment.")
        return False

    try:
        # Initialize components
        print("Initializing GitHub AI Agent...")
        settings = Settings()

        github_client = GitHubClient(
            token=settings.github_token,
            target_owner=settings.target_owner,
            target_repo=settings.target_repo,
        )

        agent = GitHubIssueAgent(
            github_client=github_client,
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

        # Get issues with the specified label
        print(
            f"Fetching issues with label '{settings.issue_label}' from {settings.target_owner}/{settings.target_repo}"
        )
        issues = github_client.get_issues_with_label(settings.issue_label)

        if not issues:
            print("No issues found with the specified label.")
            return True

        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  #{issue.number}: {issue.title}")

        # Process the first issue as an example
        if issues:
            issue = issues[0]
            print(f"\nProcessing issue #{issue.number}: {issue.title}")

            result = agent.process_issue(issue.number)

            if result.success:
                print(f"✅ Successfully processed issue #{issue.number}")
                print(
                    f"   Created PR #{result.pr_number} on branch '{result.branch_name}'"
                )
            else:
                print(
                    f"❌ Failed to process issue #{issue.number}: {result.error_message}"
                )

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = example_usage()
    sys.exit(0 if success else 1)

"""Main application for the GitHub AI Agent."""

import asyncio
import logging
import sys
import time
from typing import Set

from .agent import GitHubIssueAgent
from .logging_utils import (
    Colors,
    log_info,
    log_agent_action,
    log_section_start,
    log_github_action,
    print_separator,
)
from .config import get_settings
from .github_client import GitHubClient


# Configure clean logging - disable the default verbose logging
logging.basicConfig(
    level=logging.WARNING,  # Set to WARNING to reduce noise
    format="%(message)s",  # Simple format
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)


# Create a custom filter to hide LangGraph debug output
class LangGraphFilter(logging.Filter):
    def filter(self, record):
        # Hide verbose LangGraph state messages
        if hasattr(record, "getMessage"):
            message = record.getMessage()
            if message.startswith("[values]") or message.startswith("[updates]"):
                return False
        return True


# Apply the filter to the root logger
for handler in logging.getLogger().handlers:
    handler.addFilter(LangGraphFilter())

logger = logging.getLogger(__name__)


class GitHubAIAgentApp:
    """Main application for the GitHub AI Agent."""

    def __init__(self):
        """Initialize the application."""
        log_section_start("GitHub AI Agent Initialization")

        self.settings = get_settings()
        log_info(f"Target: {self.settings.target_owner}/{self.settings.target_repo}")
        log_info(f"Assignee filter: '{self.settings.issue_assignee}'")
        log_info(f"AI Model: {self.settings.openai_model}")
        log_info(f"Max iterations: {self.settings.max_iterations}")

        # Check if --force-app-auth is provided
        force_app_auth = len(sys.argv) > 1 and "--force-app-auth" in sys.argv

        # Initialize GitHub client using GitHub App authentication as first option only if --force-app-auth is provided
        if (
            force_app_auth
            and self.settings.github_app_id
            and self.settings.github_app_private_key_file
        ):
            self.github_client = GitHubClient(
                target_owner=self.settings.target_owner,
                target_repo=self.settings.target_repo,
                app_id=self.settings.github_app_id,
                private_key_file=self.settings.github_app_private_key_file,
                use_github_app=True,
            )
            log_github_action("Authenticated via GitHub App (forced)", "CLIENT_INIT")
        elif (
            self.settings.github_ai_agent_token
        ):  # Initialize GitHub client using token authentication for Test-AI-Agent
            self.github_client = GitHubClient(
                target_owner=self.settings.target_owner,
                target_repo=self.settings.target_repo,
                token=self.settings.github_ai_agent_token,
            )
            log_github_action("Authenticated via AI Agent Token", "CLIENT_INIT")
        elif (
            self.settings.github_token
        ):  # Initialize GitHub client using token authentication for human user
            self.github_client = GitHubClient(
                target_owner=self.settings.target_owner,
                target_repo=self.settings.target_repo,
                token=self.settings.github_token,
            )
            log_github_action("Authenticated via Personal Token", "CLIENT_INIT")
        else:
            raise ValueError(
                "Either GitHub AI Agent token (GITHUB_AI_AGENT_TOKEN) or GitHub token (GITHUB_TOKEN) must be provided"
            )

        self.agent = GitHubIssueAgent(
            github_client=self.github_client,
            openai_api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            max_iterations=self.settings.max_iterations,
            recursion_limit=self.settings.recursion_limit,
        )

        self.processed_issues: Set[int] = set()
        print_separator()

    def poll_and_process_issues(self) -> None:
        """Poll for new issues and process them."""
        log_section_start("Scanning for Issues")

        log_info(
            f"Looking for issues assigned to '{self.settings.issue_assignee}'", "POLL"
        )

        # Get issues assigned to the specified user
        issues = self.github_client.get_issues_assigned_to(self.settings.issue_assignee)

        # Filter out already processed issues
        new_issues = [
            issue for issue in issues if issue.number not in self.processed_issues
        ]

        if not new_issues:
            log_info(
                "No assigned issues found, checking for 'AI Agent' labeled issues",
                "POLL",
            )

            # Look for issues with 'AI Agent' label
            labeled_issues = self.github_client.get_issues_with_label("AI Agent")

            # Filter out already processed issues and take only the first one
            unprocessed_labeled = [
                issue
                for issue in labeled_issues
                if issue.number not in self.processed_issues
            ]

            if unprocessed_labeled:
                new_issues = [unprocessed_labeled[0]]  # Take only the first issue
                log_info(
                    f"Found issue #{new_issues[0].number} with 'AI Agent' label", "POLL"
                )
            else:
                log_info("No new issues to process")
                return

        log_info(f"Discovered {len(new_issues)} unprocessed issues", "NEW_ISSUES")
        print_separator()

        for issue in new_issues:
            try:
                log_section_start(
                    f"Processing Issue #{issue.number} Title: {issue.title}"
                )

                # Create branch immediately after detecting new issue
                branch_name = f"ai-agent/issue-{issue.number}"

                if self.github_client.create_branch(branch_name):
                    # Create draft PR immediately after branch creation
                    draft_pr_title = (
                        f"[DRAFT] Processing Issue #{issue.number}: {issue.title}"
                    )
                    draft_pr_body = f"""🤖 **AI Agent is processing this issue**

This is a draft pull request that was automatically created when the AI Agent started processing issue #{issue.number}.

## Issue Details
**Title**: {issue.title}
**Status**: 🔄 In Progress

## Progress
- ✅ Branch created: `{branch_name}`
- ✅ Draft PR created  
- 🔄 AI Agent processing...
- ⏳ Waiting for completion...

---
*This PR will be updated automatically when the AI Agent completes processing the issue.*

**Related Issue**: #{issue.number}
"""

                    draft_pr = self.github_client.create_pull_request(
                        title=draft_pr_title,
                        body=draft_pr_body,
                        head=branch_name,
                        base="main",
                        draft=True,
                    )

                    if draft_pr:
                        log_github_action(
                            f"Created draft PR #{draft_pr.number}", "DRAFT_PR"
                        )

                        # Comment on the issue about the draft PR
                        draft_comment = f"🤖 **AI Agent Started Processing**\n\nI've started processing this issue and created a draft pull request to track progress:\n\n📋 **Draft PR**: #{draft_pr.number}\n🌿 **Branch**: `{branch_name}`\n\nI'll update you when the processing is complete!"

                        self.github_client.add_comment_to_issue(
                            issue.number, draft_comment
                        )

                        # Now process the issue with the pre-created branch and draft PR
                        result = self.agent.process_issue(
                            issue.number, branch_name, draft_pr.number
                        )

                        if result.success:
                            log_github_action(
                                f"Issue completed! Updated PR #{result.pr_number} to ready",
                                "SUCCESS",
                            )
                            self.processed_issues.add(issue.number)
                        else:
                            log_github_action(
                                f"Processing failed: {result.error_message}", "FAILED"
                            )
                    else:
                        log_github_action(
                            f"Draft PR creation failed for issue #{issue.number}",
                            "FAILED",
                        )
                        continue
                else:
                    log_github_action(
                        f"Branch creation failed for issue #{issue.number}", "FAILED"
                    )
                    continue

                print_separator()

            except Exception as e:
                log_github_action(
                    f"Unexpected error processing issue #{issue.number}: {e}", "ERROR"
                )
                print_separator()

    def run_once(self) -> None:
        """Run the agent once to process current issues."""
        log_section_start("Single Run Mode")
        self.poll_and_process_issues()
        log_info("Single run completed", "COMPLETE")

    def run_daemon(self) -> None:
        """Run the agent as a daemon, continuously polling for issues."""
        log_section_start(f"Daemon Mode - Polling every {self.settings.poll_interval}s")

        try:
            while True:
                self.poll_and_process_issues()
                log_info(f"Sleeping for {self.settings.poll_interval} seconds...")
                time.sleep(self.settings.poll_interval)

        except KeyboardInterrupt:
            log_info("Daemon stopped by user", "SHUTDOWN")
        except Exception as e:
            log_info(f"Daemon error: {e}", "ERROR")
            logger.error(f"Daemon error: {e}", exc_info=True)
            raise


def main() -> None:
    """Main entry point."""
    import sys

    # Print welcome banner
    print_separator("═", 80)
    print(
        f"🤖 {Colors.AGENT_BOLD}GITHUB AI AGENT{Colors.RESET} - Automated Issue Processing"
    )
    print_separator("═", 80)

    # Set logging level from settings
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level)

    app = GitHubAIAgentApp()

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        app.run_daemon()
    else:
        app.run_once()


if __name__ == "__main__":
    main()

"""Main application for the GitHub AI Agent."""

import asyncio
import logging
import sys
import time
from typing import Set, Optional

from .agent import GitHubIssueAgent
from .logging_utils import (
    Colors,
    log_info,
    log_agent_action,
    log_section_start,
    log_github_action,
    log_error,
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
        self.last_pr_comment_check: Optional[str] = None
        print_separator()

    def poll_and_process_issues(self) -> None:
        """Poll for new issues and process them."""
        log_section_start("Scanning for Issues")

        log_info(
            f"Looking for issues assigned to '{self.settings.issue_assignee}'", "POLL"
        )

        # Get issues assigned to the specified user
        issues = self.github_client.get_issues_assigned_to(self.settings.issue_assignee)

        # Filter out already processed issues and issues being processed
        all_issues_count = len(issues)
        new_issues = [
            issue
            for issue in issues
            if issue.number not in self.processed_issues
            and not self.github_client.is_issue_being_processed(issue.number)
        ]

        skipped_count = all_issues_count - len(new_issues)
        if skipped_count > 0:
            log_info(
                f"Skipped {skipped_count} issues (already processed or being processed)",
                "FILTER",
            )

        if not new_issues:
            log_info(
                "No assigned issues found, checking for 'AI Agent' labeled issues",
                "POLL",
            )

            # Look for issues with 'AI Agent' label
            labeled_issues = self.github_client.get_issues_with_label("AI Agent")
            all_labeled_count = len(labeled_issues)

            # Filter out already processed issues and issues being processed and take only the first one
            unprocessed_labeled = [
                issue
                for issue in labeled_issues
                if issue.number not in self.processed_issues
                and not self.github_client.is_issue_being_processed(issue.number)
            ]

            skipped_labeled_count = all_labeled_count - len(unprocessed_labeled)
            if skipped_labeled_count > 0:
                log_info(
                    f"Skipped {skipped_labeled_count} labeled issues (already processed or being processed)",
                    "FILTER",
                )

            if unprocessed_labeled:
                new_issues = [unprocessed_labeled[0]]  # Take only the first issue
                log_info(
                    f"Found issue #{new_issues[0].number} with 'AI Agent' label", "POLL"
                )
            else:
                log_info("No new issues to process")
                # Even if no new issues, check for PR follow-up comments
                self.check_pr_follow_up_comments()
                return

        log_info(f"Discovered {len(new_issues)} unprocessed issues", "NEW_ISSUES")
        print_separator()

        # Process new issues first
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

        # After processing new issues, check for PR follow-up comments
        self.check_pr_follow_up_comments()

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

    def check_pr_follow_up_comments(self) -> None:
        """Check for follow-up comments on open PRs and re-process related issues."""
        log_section_start("Checking PR Follow-up Comments")

        # Get current timestamp to use for next check
        from datetime import datetime

        current_time = datetime.utcnow().isoformat() + "Z"

        # Get PRs with recent comments
        prs_with_comments = self.github_client.get_open_prs_with_recent_comments(
            since_timestamp=self.last_pr_comment_check
        )

        if not prs_with_comments:
            log_info("No follow-up comments found on open PRs", "PR_COMMENTS")
            self.last_pr_comment_check = current_time
            return

        log_info(
            f"Found {len(prs_with_comments)} PRs with recent comments", "PR_COMMENTS"
        )

        for pr_data in prs_with_comments:
            pr_number = pr_data["pr_number"]
            related_issue = pr_data["related_issue"]
            recent_comments = pr_data["recent_comments"]

            if not related_issue:
                log_info(
                    f"PR #{pr_number} has no related issue - skipping",
                    "PR_COMMENTS",
                )
                continue

            # Filter out comments from the AI agent itself to avoid loops
            user_comments = [
                comment
                for comment in recent_comments
                if not self.github_client.is_comment_from_ai_agent(comment["author"])
            ]

            if not user_comments:
                log_info(
                    f"PR #{pr_number} has no user comments (only AI agent comments) - skipping",
                    "PR_COMMENTS",
                )
                continue

            # Filter out user comments that have already been addressed by the AI Agent
            # A user comment is considered "addressed" if there's an AI agent comment after it
            unaddressed_user_comments = []

            # Sort all comments by creation time to establish chronological order
            all_comments_sorted = sorted(recent_comments, key=lambda x: x["created_at"])

            for user_comment in user_comments:
                # Check if there's an AI agent comment after this user comment
                has_ai_response = False

                for comment in all_comments_sorted:
                    # If this comment is after the user comment and is from AI agent
                    if comment["created_at"] > user_comment[
                        "created_at"
                    ] and self.github_client.is_comment_from_ai_agent(
                        comment["author"]
                    ):
                        has_ai_response = True
                        break

                # If no AI response found after this user comment, it's unaddressed
                if not has_ai_response:
                    unaddressed_user_comments.append(user_comment)

            if not unaddressed_user_comments:
                log_info(
                    f"PR #{pr_number} has no unaddressed user comments (all have AI agent responses) - skipping",
                    "PR_COMMENTS",
                )
                continue

            log_info(
                f"PR #{pr_number} has {len(unaddressed_user_comments)} unaddressed user comments (out of {len(user_comments)} total), related to issue #{related_issue}",
                "PR_COMMENTS",
            )

            try:
                # Get the issue to re-process
                issue = self.github_client.get_issue(related_issue)
                if not issue:
                    log_info(
                        f"Could not find issue #{related_issue} for PR #{pr_number}",
                        "PR_COMMENTS",
                    )
                    continue

                log_section_start(
                    f"Re-processing Issue #{related_issue} due to PR #{pr_number} comments"
                )

                # Create a context string with the unaddressed comments
                comments_context = "\n\n".join(
                    [
                        f"**Comment by {comment['author']} on {comment['created_at']}:**\n{comment['body']}"
                        for comment in all_comments_sorted  # use all comments, not just unaddressed
                    ]
                )

                # Get the existing branch for this issue
                branch_name = f"ai-agent/issue-{related_issue}"

                # Check if branch exists
                try:
                    self.github_client.repo.get_branch(branch_name)
                    branch_exists = True
                except:
                    branch_exists = False

                if not branch_exists:
                    # Create new branch if it doesn't exist
                    if not self.github_client.create_branch(branch_name):
                        log_github_action(
                            f"Failed to create branch for issue #{related_issue}",
                            "FAILED",
                        )
                        continue

                # Add a comment to the issue about re-processing
                reprocess_comment = f"""🤖 **AI Agent Re-processing Issue**

I noticed new unaddressed comments on the related pull request #{pr_number} and I'm re-processing this issue to address them.

**Unaddressed Comments:**
{comments_context}

I'll update the pull request with any necessary changes."""

                self.github_client.add_comment_to_issue(
                    related_issue, reprocess_comment
                )

                # Re-process the issue with the PR comments as context
                result = self.agent.process_issue(
                    related_issue,
                    branch_name,
                    pr_number,
                    additional_context=f"Follow-up comments from PR #{pr_number}:\n{comments_context}",
                )

                if result.success:
                    log_github_action(
                        f"Issue #{related_issue} re-processed successfully! Updated PR #{result.pr_number}",
                        "SUCCESS",
                    )

                    # Add a comment to the PR about the update
                    pr_update_comment = f"""🤖 **AI Agent Updated PR**

I've processed the recent unaddressed comments and updated this pull request accordingly.

**Processed Comments:**
{comments_context}

Please review the updated changes."""

                    # Add comment to PR
                    try:
                        pr = self.github_client.repo.get_pull(pr_number)
                        pr.create_issue_comment(pr_update_comment)
                        log_github_action(
                            f"Added update comment to PR #{pr_number}",
                            "PR_UPDATE",
                        )
                    except Exception as e:
                        log_error(f"Failed to add comment to PR #{pr_number}: {e}")

                else:
                    log_github_action(
                        f"Re-processing failed for issue #{related_issue}: {result.error_message}",
                        "FAILED",
                    )

            except Exception as e:
                log_github_action(
                    f"Unexpected error re-processing issue #{related_issue}: {e}",
                    "ERROR",
                )

        # Update the timestamp for next check
        self.last_pr_comment_check = current_time
        print_separator()


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

"""Main application for the GitHub AI Agent."""

import asyncio
import logging
import sys
import time
from typing import Set

from .agent import GitHubIssueAgent, log_info, log_agent_action
from .config import get_settings
from .github_client import GitHubClient


# Configure enhanced logging
class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for log levels."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[37m",  # White
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


# Set up logging with color support
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Apply colored formatter to console handler
console_handler = logging.getLogger().handlers[0]
console_handler.setFormatter(
    ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logger = logging.getLogger(__name__)


class GitHubAIAgentApp:
    """Main application for the GitHub AI Agent."""

    def __init__(self):
        """Initialize the application."""
        log_agent_action("Initializing GitHub AI Agent App", "APP_INIT")

        self.settings = get_settings()
        log_info(
            f"Target repository: {self.settings.target_owner}/{self.settings.target_repo}"
        )
        log_info(f"Issue label: {self.settings.issue_label}")
        log_info(f"OpenAI model: {self.settings.openai_model}")
        log_info(f"Max iterations: {self.settings.max_iterations}")
        log_info(f"Recursion limit: {self.settings.recursion_limit}")

        self.github_client = GitHubClient(
            token=self.settings.github_token,
            target_owner=self.settings.target_owner,
            target_repo=self.settings.target_repo,
        )
        log_agent_action("GitHub client initialized", "CLIENT_INIT")

        self.agent = GitHubIssueAgent(
            github_client=self.github_client,
            openai_api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            max_iterations=self.settings.max_iterations,
            recursion_limit=self.settings.recursion_limit,
        )
        log_agent_action("GitHub Issue Agent initialized", "AGENT_INIT")

        self.processed_issues: Set[int] = set()

    def poll_and_process_issues(self) -> None:
        """Poll for new issues and process them."""
        log_agent_action(
            f"Polling for issues with label '{self.settings.issue_label}' in {self.settings.target_owner}/{self.settings.target_repo}",
            "POLL",
        )

        # Get issues with the specified label
        issues = self.github_client.get_issues_with_label(self.settings.issue_label)
        log_info(
            f"Found {len(issues)} total issues with label '{self.settings.issue_label}'"
        )

        # Filter out already processed issues
        new_issues = [
            issue for issue in issues if issue.number not in self.processed_issues
        ]

        if not new_issues:
            log_info("No new issues found")
            return

        log_agent_action(f"Found {len(new_issues)} new issues to process", "NEW_ISSUES")

        for issue in new_issues:
            try:
                log_agent_action(
                    f"Processing issue #{issue.number}: {issue.title}", "ISSUE_START"
                )
                result = self.agent.process_issue(issue.number)

                if result.success:
                    log_agent_action(
                        f"Successfully processed issue #{issue.number}, created PR #{result.pr_number}",
                        "SUCCESS",
                    )
                    self.processed_issues.add(issue.number)
                else:
                    log_agent_action(
                        f"Failed to process issue #{issue.number}: {result.error_message}",
                        "FAILED",
                    )

            except Exception as e:
                log_agent_action(
                    f"Error processing issue #{issue.number}: {e}", "ERROR"
                )

    def run_once(self) -> None:
        """Run the agent once to process current issues."""
        log_agent_action("Running GitHub AI Agent (single run)", "RUN_ONCE")
        self.poll_and_process_issues()
        log_agent_action("Single run completed", "COMPLETE")

    def run_daemon(self) -> None:
        """Run the agent as a daemon, continuously polling for issues."""
        log_agent_action(
            f"Starting GitHub AI Agent daemon (polling every {self.settings.poll_interval} seconds)",
            "DAEMON_START",
        )

        try:
            while True:
                self.poll_and_process_issues()
                log_info(f"Sleeping for {self.settings.poll_interval} seconds...")
                time.sleep(self.settings.poll_interval)

        except KeyboardInterrupt:
            log_agent_action("Daemon stopped by user", "SHUTDOWN")
        except Exception as e:
            log_agent_action(f"Daemon error: {e}", "ERROR")
            logger.error(f"Daemon error: {e}", exc_info=True)
            raise


def main() -> None:
    """Main entry point."""
    import sys

    # Set logging level from settings
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level)

    log_agent_action("Starting GitHub AI Agent application", "APP_START")
    log_info(f"Log level: {settings.log_level}")

    app = GitHubAIAgentApp()

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        log_agent_action("Running in daemon mode", "MODE")
        app.run_daemon()
    else:
        log_agent_action("Running in single-run mode", "MODE")
        app.run_once()


if __name__ == "__main__":
    main()

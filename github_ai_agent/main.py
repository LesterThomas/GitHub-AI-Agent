"""Main application for the GitHub AI Agent."""

import asyncio
import logging
import time
from typing import Set

from .agent import GitHubIssueAgent
from .config import get_settings
from .github_client import GitHubClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitHubAIAgentApp:
    """Main application for the GitHub AI Agent."""

    def __init__(self):
        """Initialize the application."""
        self.settings = get_settings()
        self.github_client = GitHubClient(
            token=self.settings.github_token,
            target_owner=self.settings.target_owner,
            target_repo=self.settings.target_repo,
        )
        self.agent = GitHubIssueAgent(
            github_client=self.github_client,
            openai_api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            max_iterations=self.settings.max_iterations,
        )
        self.processed_issues: Set[int] = set()

    def poll_and_process_issues(self) -> None:
        """Poll for new issues and process them."""
        logger.info(
            f"Polling for issues with label '{self.settings.issue_label}' in {self.settings.target_owner}/{self.settings.target_repo}"
        )

        # Get issues with the specified label
        issues = self.github_client.get_issues_with_label(self.settings.issue_label)

        # Filter out already processed issues
        new_issues = [
            issue for issue in issues if issue.number not in self.processed_issues
        ]

        if not new_issues:
            logger.info("No new issues found")
            return

        logger.info(f"Found {len(new_issues)} new issues to process")

        for issue in new_issues:
            try:
                logger.info(f"Processing issue #{issue.number}: {issue.title}")
                result = self.agent.process_issue(issue.number)

                if result.success:
                    logger.info(
                        f"Successfully processed issue #{issue.number}, created PR #{result.pr_number}"
                    )
                    self.processed_issues.add(issue.number)
                else:
                    logger.error(
                        f"Failed to process issue #{issue.number}: {result.error_message}"
                    )

            except Exception as e:
                logger.error(f"Error processing issue #{issue.number}: {e}")

    def run_once(self) -> None:
        """Run the agent once to process current issues."""
        logger.info("Running GitHub AI Agent (single run)")
        self.poll_and_process_issues()
        logger.info("Single run completed")

    def run_daemon(self) -> None:
        """Run the agent as a daemon, continuously polling for issues."""
        logger.info(
            f"Starting GitHub AI Agent daemon (polling every {self.settings.poll_interval} seconds)"
        )

        try:
            while True:
                self.poll_and_process_issues()
                logger.info(f"Sleeping for {self.settings.poll_interval} seconds...")
                time.sleep(self.settings.poll_interval)

        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            raise


def main() -> None:
    """Main entry point."""
    import sys

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

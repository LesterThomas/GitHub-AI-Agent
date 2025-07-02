"""GitHub API client for polling issues and creating pull requests."""

import logging
from typing import Any, Dict, List, Optional

from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.GithubException import GithubException

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client for the AI Agent."""

    def __init__(self, token: str, target_owner: str, target_repo: str):
        """Initialize the GitHub client.

        Args:
            token: GitHub API token
            target_owner: Repository owner
            target_repo: Repository name
        """
        self.github = Github(token)
        self.target_owner = target_owner
        self.target_repo = target_repo
        self._repo: Optional[Repository] = None

    @property
    def repo(self) -> Repository:
        """Get the target repository."""
        if self._repo is None:
            self._repo = self.github.get_repo(f"{self.target_owner}/{self.target_repo}")
        return self._repo

    def get_issues_with_label(self, label: str, state: str = "open") -> List[Issue]:
        """Get issues with a specific label.

        Args:
            label: Label to filter by
            state: Issue state ('open', 'closed', 'all')

        Returns:
            List of issues with the specified label
        """
        try:
            issues = self.repo.get_issues(state=state, labels=[label])
            return list(issues)
        except GithubException as e:
            logger.error(f"Error fetching issues: {e}")
            return []

    def get_issue(self, issue_number: int) -> Optional[Issue]:
        """Get a specific issue by number.

        Args:
            issue_number: Issue number

        Returns:
            Issue object or None if not found
        """
        try:
            return self.repo.get_issue(issue_number)
        except GithubException as e:
            logger.error(f"Error fetching issue {issue_number}: {e}")
            return None

    def create_pull_request(
        self, title: str, body: str, head: str, base: str = "main", draft: bool = False
    ) -> Optional[PullRequest]:
        """Create a pull request in the SAAA repository.

        Args:
            title: PR title
            body: PR body
            head: Head branch
            base: Base branch
            draft: Whether to create as draft

        Returns:
            PullRequest object or None if creation failed
        """
        try:
            logger.info(
                f"Creating pull request in {self.target_owner}/{self.target_repo}: '{title}'"
            )
            logger.info(f"PR details - Head: {head}, Base: {base}, Draft: {draft}")
            pr = self.repo.create_pull(
                title=title, body=body, head=head, base=base, draft=draft
            )
            logger.info(
                f"Successfully created pull request #{pr.number} in {self.target_owner}/{self.target_repo}: {title}"
            )
            logger.info(f"Pull request URL: {pr.html_url}")
            return pr
        except GithubException as e:
            logger.error(
                f"Error creating pull request in {self.target_owner}/{self.target_repo}: {e}"
            )
            return None

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch in the SAAA repository.

        Args:
            branch_name: Name of the new branch
            from_branch: Branch to create from

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                f"Creating branch '{branch_name}' in {self.target_owner}/{self.target_repo} from '{from_branch}'"
            )
            ref = self.repo.get_git_ref(f"heads/{from_branch}")
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}", sha=ref.object.sha
            )
            logger.info(
                f"Successfully created branch '{branch_name}' in {self.target_owner}/{self.target_repo}"
            )
            return True
        except GithubException as e:
            logger.error(
                f"Error creating branch '{branch_name}' in {self.target_owner}/{self.target_repo}: {e}"
            )
            return False

    def create_or_update_file(
        self, path: str, content: str, message: str, branch: str = "main"
    ) -> bool:
        """Create or update a file in the SAAA repository.

        Args:
            path: File path in the repository
            content: File content
            message: Commit message
            branch: Branch to commit to

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                f"Creating/updating file '{path}' in {self.target_owner}/{self.target_repo} on branch '{branch}'"
            )
            # Try to get existing file
            try:
                file_obj = self.repo.get_contents(path, ref=branch)
                # Update existing file
                self.repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=file_obj.sha,
                    branch=branch,
                )
                logger.info(
                    f"Updated file '{path}' in {self.target_owner}/{self.target_repo}"
                )
            except GithubException:
                # Create new file
                self.repo.create_file(
                    path=path, message=message, content=content, branch=branch
                )
                logger.info(
                    f"Created file '{path}' in {self.target_owner}/{self.target_repo}"
                )
            return True
        except GithubException as e:
            logger.error(
                f"Error creating/updating file '{path}' in {self.target_owner}/{self.target_repo}: {e}"
            )
            return False

    def add_comment_to_issue(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            True if successful, False otherwise
        """
        try:
            issue = self.get_issue(issue_number)
            if issue:
                issue.create_comment(comment)
                logger.info(f"Added comment to issue #{issue_number}")
                return True
            return False
        except GithubException as e:
            logger.error(f"Error adding comment to issue {issue_number}: {e}")
            return False

    def close_issue(self, issue_number: int) -> bool:
        """Close an issue.

        Args:
            issue_number: Issue number

        Returns:
            True if successful, False otherwise
        """
        try:
            issue = self.get_issue(issue_number)
            if issue:
                issue.edit(state="closed")
                logger.info(f"Closed issue #{issue_number}")
                return True
            return False
        except GithubException as e:
            logger.error(f"Error closing issue {issue_number}: {e}")
            return False

    def get_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """Get pull requests.

        Args:
            state: Pull request state ('open', 'closed', 'all')

        Returns:
            List of pull requests with the specified state
        """
        try:
            pull_requests = self.repo.get_pulls(state=state)
            return list(pull_requests)
        except GithubException as e:
            logger.error(f"Error fetching pull requests: {e}")
            return []

    def close_pull_request(self, pr_number: int) -> bool:
        """Close a pull request.

        Args:
            pr_number: Pull request number

        Returns:
            True if successful, False otherwise
        """
        try:
            pr = self.repo.get_pull(pr_number)
            if pr:
                pr.edit(state="closed")
                logger.info(f"Closed pull request #{pr_number}")
                return True
            return False
        except GithubException as e:
            logger.error(f"Error closing pull request {pr_number}: {e}")
            return False

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Issue]:
        """Create a new issue.

        Args:
            title: Issue title
            body: Issue body
            labels: List of label names

        Returns:
            Issue object or None if creation failed
        """
        try:
            logger.info(f"Creating issue in {self.target_owner}/{self.target_repo}: '{title}'")
            issue = self.repo.create_issue(title=title, body=body, labels=labels or [])
            logger.info(f"Successfully created issue #{issue.number}: {title}")
            return issue
        except GithubException as e:
            logger.error(f"Error creating issue in {self.target_owner}/{self.target_repo}: {e}")
            return None

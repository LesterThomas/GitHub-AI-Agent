"""GitHub API client for polling issues and creating pull requests."""

import logging
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

import requests
from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.GithubException import GithubException

from .logging_utils import log_github_action, log_info, log_error

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client for the AI Agent."""

    def __init__(
        self,
        target_owner: str,
        target_repo: str,
        token: Optional[str] = None,
    ):
        """Initialize the GitHub client.

        Args:
            target_owner: Repository owner
            target_repo: Repository name
            token: GitHub API token
        """
        self.target_owner = target_owner
        self.target_repo = target_repo
        self._repo: Optional[Repository] = None

        # Use token authentication
        if token:
            log_github_action("Using GitHub token authentication")
            self.github = Github(token)
        else:
            raise ValueError("GitHub token must be provided")

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
            log_error(f"Error fetching issues: {e}")
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
            log_error(f"Error fetching issue {issue_number}: {e}")
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
            log_github_action(
                f"Creating pull request in {self.target_owner}/{self.target_repo}: '{title}'"
            )
            log_github_action(
                f"PR details - Head: {head}, Base: {base}, Draft: {draft}"
            )
            pr = self.repo.create_pull(
                title=title, body=body, head=head, base=base, draft=draft
            )
            log_github_action(
                f"Successfully created pull request #{pr.number} in {self.target_owner}/{self.target_repo}: {title}"
            )
            log_github_action(f"Pull request URL: {pr.html_url}")
            return pr
        except GithubException as e:
            log_error(
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
            # First check if the branch already exists
            try:
                existing_ref = self.repo.get_git_ref(f"heads/{branch_name}")
                log_github_action(
                    f"Branch '{branch_name}' already exists in {self.target_owner}/{self.target_repo}"
                )
                return True
            except GithubException:
                # Branch doesn't exist, continue with creation
                pass

            log_github_action(
                f"Creating branch '{branch_name}' in {self.target_owner}/{self.target_repo} from '{from_branch}'"
            )
            ref = self.repo.get_git_ref(f"heads/{from_branch}")
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}", sha=ref.object.sha
            )
            log_github_action(
                f"Successfully created branch '{branch_name}' in {self.target_owner}/{self.target_repo}"
            )
            return True
        except GithubException as e:
            log_error(
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
            log_github_action(
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
                log_github_action(
                    f"Updated file '{path}' in {self.target_owner}/{self.target_repo}"
                )
            except GithubException:
                # Create new file
                self.repo.create_file(
                    path=path, message=message, content=content, branch=branch
                )
                log_github_action(
                    f"Created file '{path}' in {self.target_owner}/{self.target_repo}"
                )
            return True
        except GithubException as e:
            log_error(
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
                log_github_action(f"Added comment to issue #{issue_number}")
                return True
            return False
        except GithubException as e:
            log_error(f"Error adding comment to issue {issue_number}: {e}")
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
                log_github_action(f"Closed issue #{issue_number}")
                return True
            return False
        except GithubException as e:
            log_error(f"Error closing issue {issue_number}: {e}")
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
            log_error(f"Error fetching pull requests: {e}")
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
                log_github_action(f"Closed pull request #{pr_number}")
                return True
            return False
        except GithubException as e:
            log_error(f"Error closing pull request {pr_number}: {e}")
            return False

    def create_issue(
        self, title: str, body: str, labels: Optional[List[str]] = None
    ) -> Optional[Issue]:
        """Create a new issue.

        Args:
            title: Issue title
            body: Issue body
            labels: List of label names

        Returns:
            Issue object or None if creation failed
        """
        try:
            log_github_action(
                f"Creating issue in {self.target_owner}/{self.target_repo}: '{title}'"
            )
            issue = self.repo.create_issue(title=title, body=body, labels=labels or [])
            log_github_action(f"Successfully created issue #{issue.number}: {title}")
            return issue
        except GithubException as e:
            log_error(
                f"Error creating issue in {self.target_owner}/{self.target_repo}: {e}"
            )
            return None

    def list_repository_contents(
        self, path: str = "", branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """List contents of a directory in the repository.

        Args:
            path: Directory path (empty string for root)
            branch: Branch to list contents from

        Returns:
            List of dictionaries with file/directory information
        """
        try:
            log_github_action(
                f"Listing contents of '{path}' in {self.target_owner}/{self.target_repo} on branch '{branch}'"
            )
            contents = self.repo.get_contents(path, ref=branch)

            # Handle both single file and directory contents
            if not isinstance(contents, list):
                contents = [contents]

            result = []
            for item in contents:
                result.append(
                    {
                        "name": item.name,
                        "path": item.path,
                        "type": item.type,  # "file" or "dir"
                        "size": item.size if item.type == "file" else None,
                        "download_url": (
                            item.download_url if item.type == "file" else None
                        ),
                    }
                )

            log_github_action(f"Found {len(result)} items in '{path}'")
            return result

        except GithubException as e:
            log_error(
                f"Error listing contents of '{path}' in {self.target_owner}/{self.target_repo}: {e}"
            )
            return []

    def get_file_content(self, file_path: str, branch: str = "main") -> Optional[str]:
        """Get the content of a specific file.

        Args:
            file_path: Path to the file in the repository
            branch: Branch to read from

        Returns:
            File content as string, or None if file not found
        """
        try:
            log_github_action(
                f"Reading file '{file_path}' from {self.target_owner}/{self.target_repo} on branch '{branch}'"
            )
            file_obj = self.repo.get_contents(file_path, ref=branch)

            # Handle the case where it's a directory (should not happen with correct usage)
            if file_obj.type != "file":
                log_error(f"Path '{file_path}' is not a file")
                return None

            content = file_obj.decoded_content.decode("utf-8")
            log_github_action(
                f"Successfully read file '{file_path}' ({len(content)} characters)"
            )
            return content

        except GithubException as e:
            log_error(
                f"Error reading file '{file_path}' from {self.target_owner}/{self.target_repo}: {e}"
            )
            return None

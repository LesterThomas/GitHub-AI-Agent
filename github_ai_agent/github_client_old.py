"""GitHub API client for polling issues and creating pull requests."""

import logging
import time
from typing import Any, Dict, List, Optional

import jwt
import requests
from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository
from github.GithubException import GithubException

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client for the AI Agent."""

    def __init__(
        self,
        target_owner: str,
        target_repo: str,
        token: Optional[str] = None,
        app_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """Initialize the GitHub client.

        Args:
            target_owner: Repository owner
            target_repo: Repository name
            token: GitHub API token (deprecated, use GitHub App instead)
            app_id: GitHub App ID
            client_id: GitHub App Client ID
            client_secret: GitHub App Client Secret
        """
        self.target_owner = target_owner
        self.target_repo = target_repo
        self._repo: Optional[Repository] = None

        # Prioritize GitHub App authentication over token
        if app_id and client_id and client_secret:
            logger.info("Using GitHub App authentication")
            self.github = self._create_github_app_client(
                app_id, client_id, client_secret
            )
        elif token:
            logger.info("Using GitHub token authentication")
            self.github = Github(token)
        else:
            raise ValueError(
                "Either GitHub App credentials (app_id, client_id, client_secret) or token must be provided"
            )

    def _create_github_app_client(
        self, app_id: str, client_id: str, client_secret: str
    ) -> Github:
        """Create GitHub client using GitHub App OAuth authentication.

        Args:
            app_id: GitHub App ID
            client_id: GitHub App Client ID
            client_secret: GitHub App Client Secret

        Returns:
            Authenticated GitHub client
        """
        logger.info(f"Attempting GitHub App authentication for App ID: {app_id}")
        
        # Method 1: Check if client_secret is actually a PAT (common user mistake)
        if client_secret.startswith("ghp_") or client_secret.startswith("github_pat_"):
            logger.info("Client secret appears to be a Personal Access Token")
            try:
                github_client = Github(client_secret)
                user = github_client.get_user()
                logger.info(f"Successfully authenticated as user: {user.login}")
                return github_client
            except Exception as e:
                logger.error(f"PAT authentication failed: {e}")

        # Method 2: Try OAuth Web Application Flow (for OAuth Apps)
        try:
            logger.info("Attempting OAuth Web Application Flow")
            access_token = self._try_oauth_app_flow(client_id, client_secret)
            if access_token:
                github_client = Github(access_token)
                user = github_client.get_user()
                logger.info(f"Successfully authenticated via OAuth as user: {user.login}")
                return github_client
        except Exception as e:
            logger.debug(f"OAuth Web Application Flow failed: {e}")

        # Method 3: Try Client Credentials Flow (for some GitHub App configurations)
        try:
            logger.info("Attempting Client Credentials Flow")
            access_token = self._try_client_credentials_flow(client_id, client_secret)
            if access_token:
                github_client = Github(access_token)
                user = github_client.get_user()
                logger.info(f"Successfully authenticated via Client Credentials as user: {user.login}")
                return github_client
        except Exception as e:
            logger.debug(f"Client Credentials Flow failed: {e}")

        # Method 4: Fallback - try using client_secret directly as token
        try:
            logger.info("Fallback: trying client_secret as direct token")
            github_client = Github(client_secret)
            user = github_client.get_user()
            logger.info(f"Successfully authenticated as user: {user.login}")
            return github_client
        except Exception as e:
            logger.debug(f"Direct token fallback failed: {e}")

        # If all methods fail, provide helpful error message
        logger.error("All GitHub App authentication methods failed.")
        logger.info("GitHub App Authentication Failed - Possible Solutions:")
        logger.info("1. Verify your GitHub App is configured correctly")
        logger.info("2. Check that your GitHub App has the correct permissions (Contents: Read/Write, Issues: Read/Write, Pull Requests: Read/Write)")
        logger.info("3. Ensure your GitHub App is installed on the target repository")
        logger.info("4. Verify the Client ID and Client Secret are correct")
        logger.info("5. If this is an OAuth App (not GitHub App), it may need different configuration")
        logger.info("6. Consider using a Personal Access Token in GITHUB_TOKEN instead")
        
        raise ValueError("GitHub App authentication failed. See logs for details.")

    def _try_oauth_app_flow(self, client_id: str, client_secret: str) -> str:
        """Try OAuth App flow with client credentials.
        
        Args:
            client_id: GitHub App Client ID
            client_secret: GitHub App Client Secret
            
        Returns:
            Access token if successful
        """
        # This is for OAuth Apps, not GitHub Apps
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json",
                "User-Agent": "EA-Agent/1.0"
            },
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials"
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                return token_data["access_token"]
        
        response.raise_for_status()
        return None

    def _try_client_credentials_flow(self, client_id: str, client_secret: str) -> str:
        """Try client credentials flow.
        
        Args:
            client_id: GitHub App Client ID
            client_secret: GitHub App Client Secret
            
        Returns:
            Access token if successful
        """
        # Alternative endpoint for client credentials
        response = requests.post(
            "https://api.github.com/app/oauth/token",
            headers={
                "Accept": "application/json",
                "User-Agent": "EA-Agent/1.0"
            },
            auth=(client_id, client_secret),
            json={
                "grant_type": "client_credentials"
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                return token_data["access_token"]
        
        response.raise_for_status()
        return None

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
            logger.info(
                f"Creating issue in {self.target_owner}/{self.target_repo}: '{title}'"
            )
            issue = self.repo.create_issue(title=title, body=body, labels=labels or [])
            logger.info(f"Successfully created issue #{issue.number}: {title}")
            return issue
        except GithubException as e:
            logger.error(
                f"Error creating issue in {self.target_owner}/{self.target_repo}: {e}"
            )
            return None

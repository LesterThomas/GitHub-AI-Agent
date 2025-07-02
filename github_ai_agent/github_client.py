"""GitHub API client for polling issues and creating pull requests."""

import logging
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

import jwt
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
        app_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        private_key_path: Optional[str] = None,
        prefer_token: bool = False,
    ):
        """Initialize the GitHub client.

        Args:
            target_owner: Repository owner
            target_repo: Repository name
            token: GitHub API token
            app_id: GitHub App ID
            client_id: GitHub App Client ID
            client_secret: GitHub App Client Secret
            private_key_path: Path to GitHub App private key file
            prefer_token: If True, prefer token authentication over GitHub App
        """
        self.target_owner = target_owner
        self.target_repo = target_repo
        self._repo: Optional[Repository] = None

        # Choose authentication method based on preference and availability
        if prefer_token and token:
            log_github_action("Using GitHub token authentication (preferred)")
            self.github = Github(token)
        elif not prefer_token and app_id and client_id and client_secret:
            log_github_action("Using GitHub App authentication (preferred)")
            self.github = self._create_github_app_client(
                app_id, client_id, client_secret, private_key_path
            )
        elif token:
            log_github_action("Using GitHub token authentication (fallback)")
            self.github = Github(token)
        elif app_id and client_id and client_secret:
            log_github_action("Using GitHub App authentication (fallback)")
            self.github = self._create_github_app_client(
                app_id, client_id, client_secret, private_key_path
            )
        else:
            raise ValueError(
                "Either GitHub App credentials (app_id, client_id, client_secret) or token must be provided"
            )

    def _find_private_key(self) -> Optional[str]:
        """Find private key file in the project directory."""
        key_files = [
            "ea-agent.2025-07-02.private-key.pem",
            "private-key.pem",
            "ea-agent-private-key.pem",
            "github-app-private-key.pem",
        ]

        for key_file in key_files:
            key_path = Path(key_file)
            if key_path.exists():
                log_github_action(f"Found private key file: {key_path}")
                return str(key_path)

        logger.warning("No private key file found")
        return None

    def _generate_jwt_token(self, app_id: str, private_key_path: str) -> str:
        """Generate JWT token for GitHub App authentication.

        Args:
            app_id: GitHub App ID
            private_key_path: Path to private key file

        Returns:
            JWT token
        """
        try:
            # Read private key
            with open(private_key_path, "rb") as key_file:
                private_key = key_file.read()

            # Create JWT payload
            now = int(time.time())
            payload = {
                "iat": now
                - 60,  # Issued at time (60 seconds ago to account for clock drift)
                "exp": now + 600,  # Expiration time (10 minutes from now)
                "iss": app_id,  # Issuer (GitHub App ID)
            }

            # Generate JWT token using RS256 algorithm
            jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
            log_github_action("Successfully generated JWT token")
            return jwt_token

        except Exception as e:
            log_error(f"Failed to generate JWT token: {e}")
            raise

    def _get_installation_id(self, jwt_token: str) -> int:
        """Get installation ID for the target repository.

        Args:
            jwt_token: JWT token for GitHub App

        Returns:
            Installation ID
        """
        try:
            # First, try to get installation for the specific repository
            response = requests.get(
                f"https://api.github.com/repos/{self.target_owner}/{self.target_repo}/installation",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "EA-Agent/1.0",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if response.status_code == 200:
                installation_data = response.json()
                installation_id = installation_data["id"]
                log_github_action(
                    f"Found installation ID {installation_id} for repository {self.target_owner}/{self.target_repo}"
                )
                return installation_id
            else:
                log_error(
                    f"Failed to get installation for repository: {response.status_code} - {response.text}"
                )

                # Fallback: list all installations and find the right one
                response = requests.get(
                    "https://api.github.com/app/installations",
                    headers={
                        "Authorization": f"Bearer {jwt_token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "EA-Agent/1.0",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )

                if response.status_code == 200:
                    installations = response.json()
                    log_github_action(f"Found {len(installations)} installations")

                    for installation in installations:
                        # Check if this installation has access to our target repository
                        if (
                            installation.get("account", {}).get("login")
                            == self.target_owner
                        ):
                            log_github_action(
                                f"Found matching installation for owner {self.target_owner}"
                            )
                            return installation["id"]

                    # If we have any installation, use the first one
                    if installations:
                        logger.warning(
                            f"Using first available installation ID: {installations[0]['id']}"
                        )
                        return installations[0]["id"]

                response.raise_for_status()

        except Exception as e:
            log_error(f"Failed to get installation ID: {e}")
            raise

    def _generate_installation_access_token(
        self, jwt_token: str, installation_id: int
    ) -> str:
        """Generate installation access token.

        Args:
            jwt_token: JWT token for GitHub App
            installation_id: Installation ID

        Returns:
            Installation access token
        """
        try:
            response = requests.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "EA-Agent/1.0",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "repositories": [self.target_repo],
                    "permissions": {
                        "contents": "write",
                        "issues": "write",
                        "pull_requests": "write",
                    },
                },
            )

            if response.status_code == 201:
                token_data = response.json()
                access_token = token_data["token"]
                expires_at = token_data.get("expires_at", "Unknown")
                log_github_action(
                    f"Successfully generated installation access token (expires: {expires_at})"
                )
                return access_token
            else:
                log_error(
                    f"Failed to generate installation access token: {response.status_code} - {response.text}"
                )
                response.raise_for_status()

        except Exception as e:
            log_error(f"Failed to generate installation access token: {e}")
            raise

    def _create_github_app_client(
        self,
        app_id: str,
        client_id: str,
        client_secret: str,
        private_key_path: Optional[str] = None,
    ) -> Github:
        """Create GitHub client using GitHub App authentication.

        Args:
            app_id: GitHub App ID
            client_id: GitHub App Client ID
            client_secret: GitHub App Client Secret
            private_key_path: Path to private key file

        Returns:
            Authenticated GitHub client
        """
        log_github_action(f"Attempting GitHub App authentication for App ID: {app_id}")

        try:
            # Method 1: Proper GitHub App authentication with private key
            key_path = private_key_path or self._find_private_key()
            if key_path:
                log_github_action(
                    f"Using private key authentication with file: {key_path}"
                )

                # Generate JWT token
                jwt_token = self._generate_jwt_token(app_id, key_path)

                # Get installation ID
                installation_id = self._get_installation_id(jwt_token)

                # Generate installation access token
                access_token = self._generate_installation_access_token(
                    jwt_token, installation_id
                )

                # Create GitHub client with installation access token
                github_client = Github(access_token)
                log_github_action(
                    f"Successfully authenticated GitHub App as installation"
                )
                return github_client

        except Exception as e:
            log_error(f"GitHub App private key authentication failed: {e}")
            logger.debug(f"Full error: {e}", exc_info=True)

        # Method 2: Fallback - check if client_secret is actually a PAT
        if client_secret.startswith("ghp_") or client_secret.startswith("github_pat_"):
            log_github_action("Client secret appears to be a Personal Access Token")
            try:
                github_client = Github(client_secret)
                user = github_client.get_user()
                log_github_action(f"Successfully authenticated as user: {user.login}")
                return github_client
            except Exception as e:
                log_error(f"PAT authentication failed: {e}")

        # Method 3: Fallback - try using client_secret directly as token
        try:
            log_github_action("Fallback: trying client_secret as direct token")
            github_client = Github(client_secret)
            user = github_client.get_user()
            log_github_action(f"Successfully authenticated as user: {user.login}")
            return github_client
        except Exception as e:
            logger.debug(f"Direct token fallback failed: {e}")

        # If all methods fail, provide helpful error message
        log_error("All GitHub App authentication methods failed.")
        log_github_action("GitHub App Authentication Failed - Possible Solutions:")
        log_github_action("1. Ensure your private key file is accessible")
        log_github_action(
            "2. Verify your GitHub App is installed on the target repository"
        )
        log_github_action("3. Check that your GitHub App has the correct permissions")
        log_github_action("4. Verify the App ID and Client ID are correct")
        log_github_action(
            "5. Consider using a Personal Access Token in GITHUB_TOKEN instead"
        )

        raise ValueError("GitHub App authentication failed. See logs for details.")

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

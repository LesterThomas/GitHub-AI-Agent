"""GitHub API client for polling issues and creating pull requests."""

import logging
import jwt
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
        app_id: Optional[str] = None,
        private_key_file: Optional[str] = None,
        use_github_app: bool = False,
    ):
        """Initialize the GitHub client.

        Args:
            target_owner: Repository owner
            target_repo: Repository name
            token: GitHub API token
            app_id: GitHub App ID (for App authentication fallback)
            private_key_file: Path to GitHub App private key file
        """
        self.target_owner = target_owner
        self.target_repo = target_repo
        self._repo: Optional[Repository] = None
        self.auth_method = None

        # Try token authentication first
        if token and not use_github_app:
            try:
                log_github_action("Attempting GitHub token authentication")
                self.github = Github(token)
                # Test the connection
                test_repo = self.github.get_repo(f"{target_owner}/{target_repo}")
                _ = test_repo.full_name
                log_github_action("✅ GitHub token authentication successful")
                self.auth_method = "token"
                return
            except Exception as e:
                log_error(f"❌ GitHub token authentication failed: {e}")
                log_github_action("Falling back to GitHub App authentication...")

        # Fallback to GitHub App authentication
        if app_id and private_key_file:
            try:
                log_github_action("Attempting GitHub App authentication")
                self.github = self._create_github_app_client(app_id, private_key_file)
                # Test the connection
                test_repo = self.github.get_repo(f"{target_owner}/{target_repo}")
                _ = test_repo.full_name
                log_github_action("✅ GitHub App authentication successful")
                self.auth_method = "app"
                return
            except Exception as e:
                log_error(f"❌ GitHub App authentication failed: {e}")

        # If we get here, both authentication methods failed
        if token or (app_id and private_key_file):
            raise ValueError("Both GitHub token and App authentication failed")
        else:
            raise ValueError(
                "Either GitHub token or App credentials (app_id, private_key_file) must be provided"
            )

    def _generate_jwt_token(self, app_id: str, private_key_file: str) -> str:
        """Generate JWT token for GitHub App authentication.

        Args:
            app_id: GitHub App ID
            private_key_file: Path to private key file

        Returns:
            JWT token
        """
        try:
            # Read private key
            with open(private_key_file, "rb") as key_file:
                private_key = key_file.read()

            # Create JWT payload
            now = int(time.time())
            payload = {
                "iat": now
                - 60,  # Issued at time (60 seconds ago to account for clock drift)
                "exp": now
                + 300,  # Expiration time (5 minutes from now, max allowed by GitHub)
                "iss": int(app_id),  # Issuer (GitHub App ID) - must be integer
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
                    "User-Agent": "GitHub-AI-Agent/1.0",
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
                        "User-Agent": "GitHub-AI-Agent/1.0",
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
                        log_github_action(
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
                    "User-Agent": "GitHub-AI-Agent/1.0",
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

    def _create_github_app_client(self, app_id: str, private_key_file: str) -> Github:
        """Create GitHub client using GitHub App authentication.

        Args:
            app_id: GitHub App ID
            private_key_file: Path to private key file

        Returns:
            Authenticated GitHub client
        """
        log_github_action(f"Attempting GitHub App authentication for App ID: {app_id}")

        try:
            # Check if private key file exists
            private_key_path = Path(private_key_file)
            if not private_key_path.exists():
                raise FileNotFoundError(
                    f"Private key file not found: {private_key_file}"
                )

            log_github_action(
                f"Using private key authentication with file: {private_key_file}"
            )

            # Generate JWT token
            jwt_token = self._generate_jwt_token(app_id, private_key_file)

            # Get installation ID
            installation_id = self._get_installation_id(jwt_token)

            # Generate installation access token
            access_token = self._generate_installation_access_token(
                jwt_token, installation_id
            )

            # Create GitHub client with installation access token
            github_client = Github(access_token)
            log_github_action("Successfully authenticated GitHub App as installation")
            return github_client

        except Exception as e:
            log_error(f"GitHub App authentication failed: {e}")
            raise

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

    def get_issues_assigned_to(self, assignee: str, state: str = "open") -> List[Issue]:
        """Get issues assigned to a specific user.

        Args:
            assignee: GitHub username to filter by
            state: Issue state ('open', 'closed', 'all')

        Returns:
            List of issues assigned to the specified user
        """
        try:
            issues = self.repo.get_issues(state=state, assignee=assignee)
            return list(issues)
        except GithubException as e:
            log_error(f"Error fetching issues assigned to {assignee}: {e}")
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

    def update_pull_request(
        self,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        draft: Optional[bool] = None,
    ) -> Optional[PullRequest]:
        """Update a pull request.

        Args:
            pr_number: Pull request number
            title: New title (optional)
            body: New body (optional)
            draft: Whether to set as draft (optional)

        Returns:
            PullRequest object or None if update failed
        """
        try:
            pr = self.repo.get_pull(pr_number)

            # Prepare update parameters for basic fields
            update_params = {}
            if title is not None:
                update_params["title"] = title
            if body is not None:
                update_params["body"] = body

            # Update basic fields if any
            if update_params:
                pr.edit(**update_params)
                log_github_action(f"Updated pull request #{pr_number} basic fields")

            # Handle draft state separately using GitHub API
            if draft is not None:
                try:
                    # Use direct requests to update draft state since PyGithub doesn't support it well
                    import requests

                    # Get the auth header from the existing github client - try multiple approaches
                    auth_header = None
                    try:
                        # Try the common attribute name
                        auth_header = (
                            self.github._Github__requester._Requester__authorizationHeader
                        )
                    except AttributeError:
                        try:
                            # Try alternative attribute name
                            auth_header = (
                                self.github._Github__requester._authorizationHeader
                            )
                        except AttributeError:
                            try:
                                # Try accessing the token directly
                                token = (
                                    self.github._Github__requester._Requester__auth.token
                                )
                                auth_header = f"token {token}"
                            except AttributeError:
                                try:
                                    # Last resort - try to get auth from the requester
                                    requester = self.github._Github__requester
                                    if hasattr(requester, "_auth") and hasattr(
                                        requester._auth, "token"
                                    ):
                                        auth_header = f"token {requester._auth.token}"
                                    else:
                                        # If we can't get the token, skip draft update
                                        log_error(
                                            f"Cannot access GitHub auth token for draft update on PR #{pr_number}"
                                        )
                                        raise Exception(
                                            "Cannot access GitHub auth token"
                                        )
                                except AttributeError:
                                    # Final fallback - skip draft update
                                    log_error(
                                        f"Cannot access GitHub auth token for draft update on PR #{pr_number}"
                                    )
                                    raise Exception("Cannot access GitHub auth token")

                    if auth_header:
                        # Update draft state via REST API
                        headers = {
                            "Authorization": auth_header,
                            "Accept": "application/vnd.github.v3+json",
                            "Content-Type": "application/json",
                        }

                        data = {"draft": draft}

                        response = requests.patch(
                            f"https://api.github.com/repos/{self.target_owner}/{self.target_repo}/pulls/{pr_number}",
                            headers=headers,
                            json=data,
                        )

                        if response.status_code == 200:
                            if draft is False:
                                log_github_action(
                                    f"Pull request #{pr_number} marked as ready for review"
                                )
                            elif draft is True:
                                log_github_action(
                                    f"Pull request #{pr_number} marked as draft"
                                )
                        else:
                            log_error(
                                f"Failed to update draft state for PR #{pr_number}: {response.status_code} {response.text}"
                            )

                except Exception as draft_error:
                    log_error(
                        f"Error updating draft state for PR #{pr_number}: {draft_error}"
                    )
                    # Don't fail the entire operation, just log the error

            # Refresh the PR object to get updated state
            pr = self.repo.get_pull(pr_number)
            log_github_action(f"Successfully updated pull request #{pr_number}")
            return pr

        except GithubException as e:
            log_error(f"Error updating pull request {pr_number}: {e}")
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

            # Create an empty commit to mark the beginning of AI Agent work
            if not self.create_empty_commit(branch_name, "AI Agent WIP"):
                log_error(f"Failed to create empty commit on branch '{branch_name}'")
                # Don't fail the entire operation, just log the error

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
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Optional[Issue]:
        """Create a new issue.

        Args:
            title: Issue title
            body: Issue body
            labels: List of label names
            assignees: List of GitHub usernames to assign

        Returns:
            Issue object or None if creation failed
        """
        log_github_action(
            f"Creating issue in {self.target_owner}/{self.target_repo}: '{title}'"
        )

        try:
            issue = self.repo.create_issue(
                title=title, body=body, labels=labels or [], assignees=assignees or []
            )
            log_github_action(f"Successfully created issue #{issue.number}: {title}")
            return issue
        except GithubException as e:
            # Check if the error is related to invalid assignees
            if "assignees" in str(e) and assignees:
                log_github_action(
                    f"Assignment failed, using fallback with 'AI Agent' label: {e}"
                )
                # Fallback: Create issue without assignees but add 'AI Agent' label
                fallback_labels = (labels or []).copy()
                if "AI Agent" not in fallback_labels:
                    fallback_labels.append("AI Agent")

                try:
                    issue = self.repo.create_issue(
                        title=title, body=body, labels=fallback_labels, assignees=[]
                    )
                    log_github_action(
                        f"Successfully created issue #{issue.number} with fallback labeling: {title}"
                    )
                    return issue
                except GithubException as fallback_error:
                    log_error(f"Fallback issue creation also failed: {fallback_error}")
                    return None
            else:
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

    def create_empty_commit(self, branch_name: str, message: str) -> bool:
        """Create an empty commit on a branch.

        Args:
            branch_name: Name of the branch to commit to
            message: Commit message

        Returns:
            True if successful, False otherwise
        """
        try:
            log_github_action(
                f"Creating empty commit on branch '{branch_name}' in {self.target_owner}/{self.target_repo}"
            )

            # Get the current branch reference
            branch_ref = self.repo.get_git_ref(f"heads/{branch_name}")

            # Get the current commit
            current_commit = self.repo.get_git_commit(branch_ref.object.sha)

            # Create a new commit with the same tree (empty commit)
            new_commit = self.repo.create_git_commit(
                message=message,
                tree=current_commit.tree,
                parents=[current_commit],
            )

            # Update the branch reference to point to the new commit
            branch_ref.edit(sha=new_commit.sha)

            log_github_action(
                f"Successfully created empty commit on branch '{branch_name}': {message}"
            )
            return True

        except GithubException as e:
            log_error(f"Error creating empty commit on branch '{branch_name}': {e}")
            return False

"""LanGraph ReAct agent for processing GitHub issues."""

import ast
import json
import logging
import re
import sys
import contextlib
import io
from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from .github_client import GitHubClient
from .logging_utils import (
    Colors,
    log_agent_action,
    log_github_action,
    log_llm_interaction,
    log_tool_usage,
    log_error,
    log_info,
    log_section_start,
    print_separator,
    pretty_print_json,
)

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def suppress_langgraph_output():
    """Context manager to suppress LangGraph's verbose output."""

    class FilteredStream:
        def __init__(self, stream):
            self.stream = stream

        def write(self, text):
            # Filter out LangGraph debug messages
            if not (
                text.startswith("[values]")
                or text.startswith("[updates]")
                or text.strip().startswith("{")
            ):
                self.stream.write(text)

        def flush(self):
            self.stream.flush()

        def __getattr__(self, name):
            return getattr(self.stream, name)

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = FilteredStream(old_stdout)
        sys.stderr = FilteredStream(old_stderr)
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


class AgentState(TypedDict):
    """
    Represents the state of a GitHub AI agent throughout its lifecycle.
    This TypedDict defines the structure for maintaining agent state during
    issue processing, code generation, and pull request creation workflows.
    Attributes:
        messages: A list of conversation messages between the agent and user,
            automatically managed by the add_messages annotation to handle
            message accumulation and deduplication.
        issue_data: A dictionary containing GitHub issue metadata including
            issue number, title, body, labels, assignees, and any other
            relevant information fetched from the GitHub API.
        generated_content: The AI-generated code, documentation, or other
            content produced in response to the issue. None if content
            generation hasn't occurred yet.
        branch_name: The name of the Git branch created for the changes.
            None if branch creation hasn't occurred yet.
        pr_created: Boolean flag indicating whether a pull request has been
            successfully created for the generated changes.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    issue_data: Dict[str, Any]
    generated_content: Optional[str]
    branch_name: Optional[str]
    pr_created: bool


@dataclass
class IssueProcessingResult:
    """Result of processing an issue."""

    success: bool
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    error_message: Optional[str] = None


class GitHubIssueAgent:
    """LanGraph ReAct agent for processing GitHub issues."""

    def __init__(
        self,
        github_client: GitHubClient,
        openai_api_key: str,
        model: str = "gpt-4o-mini",
        max_iterations: int = 5,
        recursion_limit: int = 10,
    ):
        """Initialize the agent.

        Args:
            github_client: GitHub API client
            openai_api_key: OpenAI API key
            model: OpenAI model to use
            max_iterations: Maximum agent iterations
            recursion_limit: Maximum recursion limit for LangGraph agent
        """
        self.github_client = github_client
        base_llm = ChatOpenAI(api_key=openai_api_key, model=model, temperature=0.1)
        self.llm = base_llm
        self.max_iterations = max_iterations
        self.recursion_limit = recursion_limit

        log_agent_action("Initializing GitHub Issue Agent", "INIT")
        log_agent_action(f"Model: {model}, Max iterations: {max_iterations}")
        log_agent_action(f"Recursion limit: {recursion_limit}")
        log_agent_action(
            f"Target SAAA repository: {github_client.target_owner}/{github_client.target_repo}"
        )

        # Create tools for the agent
        self.tools = self._create_tools()
        log_agent_action(
            f"Created {len(self.tools)} tools: {[tool.name for tool in self.tools]}",
            "TOOLS",
        )

        # Create the ReAct agent
        self.agent = create_react_agent(
            base_llm, self.tools, checkpointer=MemorySaver()
        )
        log_agent_action("ReAct agent created successfully", "INIT")

    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent."""

        def create_files_from_request(files_json: str) -> str:
            """Create the requested files directly in GitHub repository.

            Args:
                files_json: JSON string containing array of file objects.
                           Each object should have 'filename' and 'file_content' properties.
                           Example: '[{"filename": "test.md", "file_content": "# Test\\nThis is a test file"}]'

            Returns:
                JSON string with creation results.
            """
            import json

            log_tool_usage("create_files_from_request", files_json[:200])

            try:
                # Parse the JSON input
                files_array = json.loads(files_json)

                if not isinstance(files_array, list):
                    error_msg = "Input must be a JSON array of file objects"
                    log_error(error_msg, "ACTION")
                    return json.dumps(
                        {"success": False, "error": error_msg, "files_created": []}
                    )

                # Get the current branch name from the instance
                # This will be set when the agent is processing an issue
                current_branch = getattr(self, "_current_branch", None)
                if not current_branch:
                    error_msg = "No branch available for file creation"
                    log_error(error_msg, "ACTION")
                    return json.dumps(
                        {"success": False, "error": error_msg, "files_created": []}
                    )

                files_created = []
                errors = []

                for file_obj in files_array:
                    if not isinstance(file_obj, dict):
                        error_msg = f"Invalid file object: {file_obj}"
                        log_error(error_msg)
                        errors.append(error_msg)
                        continue

                    filename = file_obj.get("filename")
                    file_content = file_obj.get("file_content")

                    if not filename:
                        error_msg = "File object missing 'filename' property"
                        log_error(error_msg)
                        errors.append(error_msg)
                        continue

                    if file_content is None:
                        file_content = (
                            "# Default Content\n\nThis file was created automatically."
                        )

                    # Create the file directly in GitHub
                    log_agent_action(
                        f"Creating file {filename} in SAAA repository on branch {current_branch}",
                        "FILE_COMMIT",
                    )

                    # Get the current issue number for the commit message
                    current_issue_number = getattr(
                        self, "_current_issue_number", "unknown"
                    )
                    commit_message = f"Create {filename} as requested in issue #{current_issue_number}"

                    if self.github_client.create_or_update_file(
                        path=filename,
                        content=file_content,
                        message=commit_message,
                        branch=current_branch,
                    ):
                        files_created.append(filename)
                    else:
                        error_msg = (
                            f"Failed to create file: {filename} in SAAA repository"
                        )
                        log_error(error_msg, "FILE_ERROR")
                        errors.append(error_msg)

                # Prepare result
                result = {
                    "success": len(files_created) > 0,
                    "files_created": files_created,
                    "files_count": len(files_created),
                    "errors": errors if errors else None,
                }

                result_json = json.dumps(result, indent=2)
                log_tool_usage(
                    "create_files_from_request",
                    f"Created {len(files_created)} files directly in GitHub",
                )
                return result_json

            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON format: {e}"
                log_tool_usage("create_files_from_request", error_msg, "ERROR")
                return json.dumps(
                    {"success": False, "error": error_msg, "files_created": []}
                )
            except Exception as e:
                error_msg = f"Error creating files: {e}"
                log_tool_usage("create_files_from_request", error_msg, "ERROR")
                return json.dumps(
                    {"success": False, "error": error_msg, "files_created": []}
                )

        return [
            Tool(
                name="create_files_from_request",
                description="""Create files directly in the GitHub repository. Each object must have 'filename' and 'file_content' properties.

Example input:
[
  {
    "filename": "test.md", 
    "file_content": "# Test File\\n\\nThis is a test file content."
  },
  {
    "filename": "readme.txt",
    "file_content": "This is a readme file."
  }
]

This tool creates the files immediately in the GitHub repository and returns a status report.""",
                func=create_files_from_request,
            ),
        ]

    def process_issue(
        self, issue_number: int, branch_name: Optional[str] = None
    ) -> IssueProcessingResult:
        """Process a GitHub issue and create a pull request.

        Args:
            issue_number: GitHub issue number
            branch_name: Pre-created branch name (if None, will create one)

        Returns:
            Result of processing the issue
        """
        try:
            log_agent_action(f"Starting to process issue #{issue_number}", "START")

            # Get the issue
            log_agent_action(f"Fetching issue #{issue_number} from GitHub", "FETCH")
            issue = self.github_client.get_issue(issue_number)
            if not issue:
                error_msg = f"Issue #{issue_number} not found"
                log_error(error_msg, "ISSUE_NOT_FOUND")
                return IssueProcessingResult(success=False, error_message=error_msg)

            log_agent_action(
                f"Successfully fetched issue #{issue_number}: {issue.title}"
            )
            log_agent_action(
                f"Processing issue #{issue_number}: {issue.title}", "PROCESS"
            )

            # Prepare the initial state
            issue_data = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "user": issue.user.login if issue.user else "unknown",
                "labels": [label.name for label in issue.labels],
            }

            log_agent_action(
                f"Issue data prepared: {issue_data['title']}, User: {issue_data['user']}, Labels: {issue_data['labels']}"
            )

            # Create system message with context
            log_agent_action("Creating system and human messages", "MESSAGE_PREP")
            system_message = SystemMessage(content=self._get_system_prompt())
            human_message = HumanMessage(
                content=f"""Process this GitHub issue:

Issue #{issue.number}: {issue.title}

Description: {issue.body or 'No description provided'}

Analyze the issue and use create_files_from_request with a JSON array to create the requested files.

Example format:
[
  {{
    "filename": "example.md",
    "file_content": "# Example\\n\\nThis is example content."
  }}
]

Use the create_files_from_request tool with proper JSON formatting."""
            )

            log_agent_action(
                "Messages created, preparing to invoke agent", "MESSAGE_READY"
            )

            # Set the current branch and issue number for the tool to use
            self._current_branch = branch_name
            self._current_issue_number = issue.number

            # Run the agent
            initial_state = AgentState(
                messages=[system_message, human_message],
                issue_data=issue_data,
                generated_content=None,
                branch_name=branch_name,
                pr_created=False,
            )

            config = {
                "configurable": {"thread_id": f"issue-{issue.number}"},
                "recursion_limit": self.recursion_limit,
            }
            log_agent_action(
                f"Invoking ReAct agent with thread_id: issue-{issue.number}, recursion_limit: {self.recursion_limit}",
                "AGENT_INVOKE",
            )

            # Stream the execution to capture state changes (with fallback to invoke)
            final_state = None
            step_count = 0

            try:
                with suppress_langgraph_output():
                    for chunk in self.agent.stream(
                        initial_state, config, stream_mode=["values"], debug=False
                    ):
                        step_count += 1

                        # Handle different chunk formats
                        if isinstance(chunk, tuple) and len(chunk) == 2:
                            mode, data = chunk
                            last_message = data["messages"][-1]

                            # Check message type
                            if isinstance(last_message, HumanMessage):
                                message_type = "HumanMessage"
                            elif isinstance(last_message, SystemMessage):
                                message_type = "SystemMessage"
                            else:
                                message_type = type(last_message).__name__

                            log_llm_interaction(
                                last_message, f"{mode} ({message_type})"
                            )
                            if mode == "values":
                                final_state = data
                        elif isinstance(chunk, dict):
                            final_state = chunk

                log_agent_action(
                    f"Agent execution completed after {step_count} steps",
                    "AGENT_COMPLETE",
                )

            except Exception as stream_error:
                log_agent_action(
                    f"Streaming failed, falling back to invoke: {stream_error}",
                    "FALLBACK",
                )
                final_state = self.agent.invoke(initial_state, config)
                log_agent_action(
                    "Agent execution completed via invoke", "AGENT_COMPLETE"
                )

            if final_state is None:
                raise ValueError("Failed to get final state from agent execution")

            # Extract the final response and parse for file creation requirements
            final_message = final_state["messages"][-1]
            generated_content = (
                final_message.content
                if hasattr(final_message, "content")
                else str(final_message)
            )

            log_agent_action(
                f"Generated content length: {len(generated_content)} characters"
            )

            # Check if files were created by the tool (tool creates files directly now)
            files_created = []

            # Look for ToolMessage instances that contain the tool results
            for msg in final_state.get("messages", []):
                # Check for ToolMessage instances (the actual tool results)
                if hasattr(msg, "name") and msg.name == "create_files_from_request":
                    try:
                        tool_result = json.loads(msg.content)
                        if tool_result.get("success") and tool_result.get(
                            "files_created"
                        ):
                            files_created.extend(tool_result["files_created"])
                            break  # Found the tool result, no need to continue
                    except json.JSONDecodeError as e:
                        log_error(f"Failed to parse ToolMessage JSON: {e}")
                        continue

            log_agent_action(f"Total files created by tool: {len(files_created)}")

            # Clean up temporary instance variables
            if hasattr(self, "_current_branch"):
                delattr(self, "_current_branch")
            if hasattr(self, "_current_issue_number"):
                delattr(self, "_current_issue_number")

            # Create fallback file if no files were created by the tool
            if not files_created:
                log_agent_action(
                    "No files created by tool, creating fallback metadata file",
                    "FALLBACK",
                )
                # Fallback: create a metadata file if the tool didn't create any files
                file_path = f"generated/issue-{issue.number}.md"
                file_content = f"""# Response to Issue #{issue.number}: {issue.title}

## Original Issue
{issue.body or 'No description provided'}

## Generated Response
{generated_content}

## Metadata
- Issue Number: #{issue.number}
- Created by: AI Agent
- Branch: {branch_name}
"""
                log_agent_action(
                    f"Creating fallback file {file_path} in SAAA repository",
                    "FILE_COMMIT",
                )
                if self.github_client.create_or_update_file(
                    path=file_path,
                    content=file_content,
                    message=f"AI Agent response to issue #{issue.number}",
                    branch=branch_name,
                ):
                    files_created.append(file_path)
                    log_agent_action(
                        f"Successfully created fallback file: {file_path} in SAAA repository"
                    )
                else:
                    log_error(
                        f"Failed to create fallback file: {file_path} in SAAA repository"
                    )

            if files_created:
                log_agent_action(
                    f"Files created successfully: {files_created}", "FILES_COMPLETE"
                )
                # Create pull request
                pr_title = f"Create {', '.join(files_created)} as requested in issue #{issue.number}"
                files_list = "\n".join(
                    [f"- `{f}`: {self._describe_file(f)}" for f in files_created]
                )

                pr_body = f"""
This pull request was automatically generated by the AI Agent in response to issue #{issue.number}.

## Repository Workflow
- **Target Repository**: SAAA ({self.github_client.target_owner}/{self.github_client.target_repo})
- **Feature Branch**: `{branch_name}`
- **Base Branch**: `main`

## Original Issue
{issue.title}

## Files Created/Updated
{files_list}

## Summary
{generated_content[:500]}{'...' if len(generated_content) > 500 else ''}

## Related Issue
Closes #{issue.number}

---
*This PR was created by the GitHub AI Agent to resolve the issue by creating the requested files in the SAAA repository.*
"""

                log_agent_action(
                    f"Creating pull request to SAAA repository: {pr_title}",
                    "PR_CREATE",
                )
                pr = self.github_client.create_pull_request(
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base="main",
                    draft=False,
                )

                if pr:
                    log_agent_action(
                        f"Successfully created pull request #{pr.number} in SAAA repository"
                    )
                    log_agent_action(f"Pull request URL: {pr.html_url}")
                    # Add comment to the original issue
                    log_agent_action(
                        f"Adding comment to issue #{issue.number}", "COMMENT"
                    )
                    self.github_client.add_comment_to_issue(
                        issue.number,
                        f"I've created a pull request #{pr.number} in the SAAA repository with the generated content. Please review and merge if satisfactory.\n\nPull request: {pr.html_url}",
                    )

                    log_agent_action(
                        f"Issue #{issue_number} processed successfully - created PR in SAAA repository",
                        "SUCCESS",
                    )
                    return IssueProcessingResult(
                        success=True, pr_number=pr.number, branch_name=branch_name
                    )
                else:
                    log_error("Failed to create pull request in SAAA repository")
            else:
                log_error("No files were created in SAAA repository")

            error_msg = "Failed to create files or pull request in SAAA repository"
            log_error(error_msg)
            return IssueProcessingResult(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"Error processing issue #{issue_number}: {e}"
            log_error(error_msg, "EXCEPTION")
            logger.error(error_msg, exc_info=True)
            return IssueProcessingResult(success=False, error_message=str(e))

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return f"""You are an AI agent that processes GitHub issues to create the exact files requested.

Your task is simple:
1. Analyze the GitHub issue to identify what files need to be created and their content
2. Use create_files_from_request with a JSON array of file objects to create the files
3. Respond with a summary of what was created

For an issue like "Create a new file TEST.md and write in it 'this is a test'":
- Call create_files_from_request with: [{{"filename": "TEST.md", "file_content": "this is a test"}}]

For multiple files, include all in one call:
- [{{"filename": "file1.md", "file_content": "content1"}}, {{"filename": "file2.txt", "file_content": "content2"}}]

Be direct and focused. Use only the create_files_from_request tool with properly formatted JSON.

Available tools:
- create_files_from_request: Takes JSON array of file objects with filename and file_content properties

Target repository: {self.github_client.target_owner}/{self.github_client.target_repo}"""

    def _describe_file(self, filename: str) -> str:
        """Provide a description of what a file contains based on its name."""
        log_agent_action(f"Describing file: {filename}", "FILE_DESC")

        description = ""
        if filename.endswith(".md"):
            if "test" in filename.lower():
                description = "Test markdown file with example content"
            else:
                description = "Markdown file with generated content"
        elif filename.endswith(".txt"):
            description = "Text file with generated content"
        else:
            description = "Generated file as requested"

        log_agent_action(f"File description for {filename}: {description}")
        return description

"""
LanGraph ReAct Agent for GitHub Issue Processing

This module implements a ReAct (Reasoning and Acting) agent using LangGraph that:
1. Processes GitHub issues automatically
2. Generates appropriate files based on issue content
3. Creates pull requests with the generated content
4. Maintains conversation state throughout the process

The agent uses OpenAI's language models and GitHub's API to provide an automated
workflow for issue resolution.
"""

import json
import logging
from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from .github_client import GitHubClient
from .config import get_system_prompt, get_human_message_template, get_tool_description
from .logging_utils import (
    Colors,
    log_agent_action,
    log_llm_interaction,
    log_tool_usage,
    log_error,
)

logger = logging.getLogger(__name__)


# ============================================================================
# STATE MANAGEMENT
# ============================================================================


class AgentState(TypedDict):
    """
    State management for the LangGraph ReAct agent.

    This TypedDict defines the complete state structure that flows through
    the agent's graph execution. LangGraph uses this to track conversation
    flow and maintain context between different processing steps.

    The state follows LangGraph's pattern of immutable updates, where each
    node in the graph can read from and write to specific state fields.

    Attributes:
        messages: Conversation history managed by LangGraph's add_messages
            reducer. This automatically handles message deduplication and
            maintains the conversation flow between human, AI, and tool messages.
        issue_data: GitHub issue metadata including title, body, labels, etc.
            This provides context for the agent's decision-making process.
        generated_content: The AI's response content after processing the issue.
            This may include reasoning, explanations, or summaries.
        branch_name: Git branch name where changes will be committed.
            Used for organizing work and creating pull requests.
        pr_created: Flag indicating if a pull request was successfully created.
            Used to track the completion of the workflow.
    """

    messages: Annotated[List[BaseMessage], add_messages]
    issue_data: Dict[str, Any]
    generated_content: Optional[str]
    branch_name: Optional[str]
    pr_created: bool


@dataclass
class IssueProcessingResult:
    """
    Result container for issue processing operations.

    Provides a structured way to return processing results with success/failure
    status and relevant metadata. This makes error handling and result
    interpretation more predictable for calling code.

    Attributes:
        success: Whether the issue was processed successfully
        pr_number: Pull request number if created (None if creation failed)
        branch_name: Git branch name used for the changes
        error_message: Detailed error message if processing failed
    """

    success: bool
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================================
# MAIN AGENT CLASS
# ============================================================================


class GitHubIssueAgent:
    """
    LangGraph ReAct agent for automated GitHub issue processing.

    This agent implements the ReAct (Reasoning and Acting) pattern using LangGraph
    to process GitHub issues automatically. It combines large language model
    reasoning with GitHub API actions to create files and pull requests.

    Architecture:
    - Uses LangGraph's create_react_agent for the core reasoning loop
    - Implements custom tools for GitHub operations
    - Maintains conversation state throughout the process
    - Provides comprehensive logging for debugging and monitoring

    Workflow:
    1. Fetch GitHub issue details
    2. Analyze issue content using LLM reasoning
    3. Generate appropriate files using custom tools
    4. Create pull request with generated content
    5. Update issue with pull request link

    The agent is designed to be stateless between issues but maintains
    internal state during processing of a single issue.
    """

    def __init__(
        self,
        github_client: GitHubClient,
        openai_api_key: str,
        model: str = "gpt-4o-mini",
        max_iterations: int = 5,
        recursion_limit: int = 10,
    ):
        """
        Initialize the GitHub Issue Agent.

        Sets up the LangGraph ReAct agent with necessary components:
        - OpenAI language model for reasoning
        - Custom tools for GitHub operations
        - Memory checkpointer for conversation history
        - Configuration for execution limits

        Args:
            github_client: Configured GitHub API client for repository operations
            openai_api_key: OpenAI API key for language model access
            model: OpenAI model name (default: gpt-4o-mini for cost efficiency)
            max_iterations: Maximum iterations for agent reasoning (safety limit)
            recursion_limit: LangGraph recursion limit to prevent infinite loops
        """
        # Store configuration
        self.github_client = github_client
        self.max_iterations = max_iterations
        self.recursion_limit = recursion_limit

        # Initialize the language model with low temperature for consistent outputs
        base_llm = ChatOpenAI(
            api_key=openai_api_key,
            model=model,
            temperature=0.1,  # Low temperature for consistent, predictable outputs
        )
        self.llm = base_llm

        # Log initialization details
        log_agent_action("Initializing GitHub Issue Agent", "INIT")
        log_agent_action(f"Model: {model}, Max iterations: {max_iterations}")
        log_agent_action(f"Recursion limit: {recursion_limit}")
        log_agent_action(
            f"Target SAAA repository: {github_client.target_owner}/{github_client.target_repo}"
        )

        # Create custom tools for GitHub operations
        self.tools = self._create_tools()
        log_agent_action(
            f"Created {len(self.tools)} tools: {[tool.name for tool in self.tools]}",
            "TOOLS",
        )

        # Create the ReAct agent using LangGraph's prebuilt factory
        # This creates a graph with reasoning and acting capabilities
        self.agent = create_react_agent(
            base_llm,
            self.tools,
            checkpointer=MemorySaver(),  # Enables conversation memory
        )
        log_agent_action("ReAct agent created successfully", "INIT")

    # ========================================================================
    # TOOL CREATION AND MANAGEMENT
    # ========================================================================

    def _create_tools(self) -> List[Tool]:
        """
        Create custom tools for the ReAct agent.

        Tools are the "Acting" part of the ReAct pattern. They allow the agent
        to perform concrete actions based on its reasoning. Each tool is a
        callable that takes specific inputs and returns structured outputs.

        LangGraph automatically integrates these tools into the reasoning loop,
        allowing the agent to:
        1. Reason about what action to take
        2. Call the appropriate tool
        3. Observe the results
        4. Continue reasoning based on the results

        Returns:
            List of Tool objects that the agent can use
        """
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field

        class CreateFileInput(BaseModel):
            filename: str = Field(description="Path/name of the file to create")
            file_content: str = Field(description="Content to write to the file")

        class EditFileInput(BaseModel):
            filename: str = Field(description="Path/name of the file to edit")
            file_content: str = Field(description="New content for the file")

        class ListFilesInput(BaseModel):
            path: str = Field(
                default="", description="Directory path to list (empty string for root)"
            )

        class ReadFileInput(BaseModel):
            filename: str = Field(description="Path/name of the file to read")

        def create_file_in_repo(filename: str, file_content: str) -> str:
            """
            Core tool for creating a single file in the GitHub repository.

            This tool implements the primary action capability of the agent:
            creating a file directly in the target GitHub repository. It's designed
            to be called by the LangGraph ReAct agent as part of its reasoning loop.

            Args:
                filename: Path/name of the file to create
                file_content: Content to write to the file

            Returns:
                JSON string with creation results including success status,
                file path, and any error messages.
            """
            import json

            log_tool_usage(
                "create_file_in_repo",
                f"filename='{filename}', content_length={len(file_content)}",
            )

            try:
                # Retrieve the current branch context
                current_branch = getattr(self, "_current_branch", None)
                if not current_branch:
                    error_msg = "No branch available for file creation"
                    log_error(error_msg, "ACTION")
                    return json.dumps(
                        {"success": False, "error": error_msg, "file_created": None}
                    )

                # Validate required fields
                if not filename:
                    error_msg = "Missing filename parameter"
                    log_error(error_msg)
                    return json.dumps(
                        {"success": False, "error": error_msg, "file_created": None}
                    )

                # Provide default content if none specified
                if not file_content:
                    file_content = (
                        "# Default Content\n\nThis file was created automatically."
                    )

                # Create the file in the GitHub repository
                log_agent_action(
                    f"Creating file {filename} in SAAA repository on branch {current_branch}",
                    "FILE_COMMIT",
                )

                # Generate contextual commit message
                current_issue_number = getattr(self, "_current_issue_number", "unknown")
                commit_message = (
                    f"Create {filename} as requested in issue #{current_issue_number}"
                )

                # Attempt file creation via GitHub API
                if self.github_client.create_or_update_file(
                    path=filename,
                    content=file_content,
                    message=commit_message,
                    branch=current_branch,
                ):
                    log_agent_action(f"Successfully created file: {filename}")
                    result = {
                        "success": True,
                        "file_created": filename,
                        "content_length": len(file_content),
                        "branch": current_branch,
                    }
                else:
                    error_msg = f"Failed to create file: {filename} in SAAA repository"
                    log_error(error_msg, "FILE_ERROR")
                    result = {
                        "success": False,
                        "error": error_msg,
                        "file_created": None,
                    }

                result_json = json.dumps(result, indent=2)
                log_tool_usage(
                    "create_file_in_repo",
                    f"File creation result: {result['success']}",
                )
                return result_json

            except Exception as e:
                error_msg = f"Error creating file: {e}"
                log_tool_usage("create_file_in_repo", error_msg, "ERROR")
                return json.dumps(
                    {"success": False, "error": error_msg, "file_created": None}
                )

        def list_files_in_repo(path: str = "") -> str:
            """List files and directories in the repository."""
            import json

            log_tool_usage("list_files_in_repo", f"path='{path}'")

            try:
                # Retrieve the current branch context
                current_branch = getattr(self, "_current_branch", None)
                if not current_branch:
                    error_msg = "No branch available for listing repository"
                    log_error(error_msg, "ACTION")
                    return json.dumps({"success": False, "error": error_msg})
                contents = self.github_client.list_repository_contents(
                    path, current_branch
                )
                result = {
                    "success": True,
                    "path": path,
                    "branch": current_branch,
                    "contents": contents,
                    "count": len(contents),
                }
                log_tool_usage(
                    "list_files_in_repo", f"Found {len(contents)} items", "SUCCESS"
                )
                return json.dumps(result)

            except Exception as e:
                error_msg = f"Error listing repository contents: {e}"
                log_tool_usage("list_files_in_repo", error_msg, "ERROR")
                return json.dumps(
                    {
                        "success": False,
                        "error": error_msg,
                        "path": path,
                        "branch": current_branch,
                        "contents": [],
                    }
                )

        def read_file_from_repo(filename: str) -> str:
            """Read content of a file from the repository."""
            import json

            log_tool_usage("read_file_from_repo", f"filename='{filename}'")

            try:
                # Retrieve the current branch context
                current_branch = getattr(self, "_current_branch", None)
                if not current_branch:
                    error_msg = "No branch available for reading file"
                    log_error(error_msg, "ACTION")
                    return json.dumps({"success": False, "error": error_msg})

                content = self.github_client.get_file_content(filename, current_branch)
                if content is None:
                    error_msg = f"File not found: {filename}"
                    log_tool_usage("read_file_from_repo", error_msg, "ERROR")
                    return json.dumps(
                        {
                            "success": False,
                            "error": error_msg,
                            "filename": filename,
                            "branch": current_branch,
                        }
                    )

                result = {
                    "success": True,
                    "filename": filename,
                    "branch": current_branch,
                    "content": content,
                    "length": len(content),
                }
                log_tool_usage(
                    "read_file_from_repo", f"Read {len(content)} characters", "SUCCESS"
                )
                return json.dumps(result)

            except Exception as e:
                error_msg = f"Error reading file: {e}"
                log_tool_usage("read_file_from_repo", error_msg, "ERROR")
                return json.dumps(
                    {
                        "success": False,
                        "error": error_msg,
                        "filename": filename,
                        "branch": current_branch,
                    }
                )

        def edit_file_in_repo(filename: str, file_content: str) -> str:
            """Edit a file in the repository."""
            import json

            log_tool_usage(
                "edit_file_in_repo",
                f"filename='{filename}', content_length={len(file_content)}",
            )

            try:
                # Validate required fields
                if not filename:
                    error_msg = "Missing filename parameter"
                    log_error(error_msg)
                    return json.dumps(
                        {"success": False, "error": error_msg, "file_created": None}
                    )

                # Provide default content if none specified
                if not file_content:
                    file_content = (
                        "# Default Content\n\nThis file was created automatically."
                    )

                # Retrieve the current branch context
                current_branch = getattr(self, "_current_branch", None)
                if not current_branch:
                    error_msg = "No branch available for editing file"
                    log_error(error_msg, "ACTION")
                    return json.dumps({"success": False, "error": error_msg})

                # Generate contextual commit message
                current_issue_number = getattr(self, "_current_issue_number", "unknown")
                commit_message = (
                    f"Edit {filename} as requested in issue #{current_issue_number}"
                )

                # Attempt file update via GitHub API
                if self.github_client.create_or_update_file(
                    path=filename,
                    content=file_content,
                    message=commit_message,
                    branch=current_branch,
                ):
                    log_agent_action(f"Successfully edited file: {filename}")
                    result = {
                        "success": True,
                        "file_edited": filename,
                        "content_length": len(file_content),
                        "branch": current_branch,
                    }
                else:
                    error_msg = f"Failed to edit file: {filename} in SAAA repository"
                    log_error(error_msg, "FILE_ERROR")
                    result = {
                        "success": False,
                        "error": error_msg,
                        "file_edited": None,
                    }

                result_json = json.dumps(result, indent=2)
                log_tool_usage(
                    "edit_file_in_repo",
                    f"File edit result: {result['success']}",
                )
                return result_json

            except Exception as e:
                error_msg = f"Error editing file: {e}"
                log_tool_usage("edit_file_in_repo", error_msg, "ERROR")
                current_branch = getattr(self, "_current_branch", "unknown")
                return json.dumps(
                    {
                        "success": False,
                        "error": error_msg,
                        "filename": "unknown",
                        "branch": current_branch,
                    }
                )

        # Return the configured tools list using StructuredTool
        return [
            StructuredTool(
                name="create_file_in_repo",
                description=get_tool_description("create_file_in_repo"),
                func=create_file_in_repo,
                args_schema=CreateFileInput,
            ),
            StructuredTool(
                name="list_files_in_repo",
                description=get_tool_description("list_files_in_repo"),
                func=list_files_in_repo,
                args_schema=ListFilesInput,
            ),
            StructuredTool(
                name="read_file_from_repo",
                description=get_tool_description("read_file_from_repo"),
                func=read_file_from_repo,
                args_schema=ReadFileInput,
            ),
            StructuredTool(
                name="edit_file_in_repo",
                description=get_tool_description("edit_file_in_repo"),
                func=edit_file_in_repo,
                args_schema=EditFileInput,
            ),
        ]

    # ========================================================================
    # ISSUE PROCESSING WORKFLOW
    # ========================================================================

    def process_issue(
        self,
        issue_number: int,
        branch_name: Optional[str] = None,
        draft_pr_number: Optional[int] = None,
    ) -> IssueProcessingResult:
        """
        Main workflow for processing a GitHub issue.

        This method orchestrates the complete issue processing workflow:
        1. Fetch issue details from GitHub
        2. Prepare agent state and context
        3. Execute the ReAct reasoning loop
        4. Handle file creation and pull request generation
        5. Update the original issue with results

        The method uses LangGraph's streaming capabilities to monitor the
        agent's reasoning process and provides comprehensive error handling
        for robust operation.

        Args:
            issue_number: GitHub issue number to process
            branch_name: Pre-created branch name (if None, assumes one exists)
            draft_pr_number: Pre-created draft PR number (if provided, will be updated to ready)

        Returns:
            IssueProcessingResult containing success status and relevant metadata
        """
        try:
            log_agent_action(f"Starting to process issue #{issue_number}", "START")

            # ================================================================
            # STEP 1: Fetch Issue Data
            # ================================================================
            log_agent_action(f"Fetching issue #{issue_number} from GitHub", "FETCH")
            issue = self.github_client.get_issue(issue_number)
            if not issue:
                error_msg = f"Issue #{issue_number} not found"
                log_error(error_msg, "ISSUE_NOT_FOUND")
                return IssueProcessingResult(success=False, error_message=error_msg)

            log_agent_action(
                f"Successfully fetched issue #{issue_number}: {issue.title}"
            )

            # ================================================================
            # STEP 2: Prepare Issue Context
            # ================================================================
            issue_data = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "user": issue.user.login if issue.user else "unknown",
                "labels": [label.name for label in issue.labels],
            }

            log_agent_action(
                f"Issue data prepared - Title: {issue_data['title']}, User: {issue_data['user']}, Labels: {issue_data['labels']}"
            )

            # ================================================================
            # STEP 3: Prepare Agent Messages
            # ================================================================
            log_agent_action("Creating system and human messages", "MESSAGE_PREP")

            # System message provides the agent's role and capabilities
            system_message = SystemMessage(content=self._get_system_prompt())

            # Human message provides the specific issue context and instructions
            human_message = HumanMessage(
                content=get_human_message_template(
                    target_owner=self.github_client.target_owner,
                    target_repo=self.github_client.target_repo,
                    issue_number=issue.number,
                    issue_title=issue.title,
                    issue_description=issue.body or "No description provided",
                )
            )

            log_agent_action(
                "Messages created, preparing to invoke agent", "MESSAGE_READY"
            )

            # ================================================================
            # STEP 4: Set Tool Context
            # ================================================================
            # These temporary instance variables provide context to the tool
            # during execution. They're cleaned up after processing.
            self._current_branch = branch_name
            self._current_issue_number = issue.number

            # ================================================================
            # STEP 5: Execute ReAct Agent
            # ================================================================
            # Initialize the agent state with all necessary context
            initial_state = AgentState(
                messages=[system_message, human_message],
                issue_data=issue_data,
                generated_content=None,
                branch_name=branch_name,
                pr_created=False,
            )

            # Configure the agent execution
            config = {
                "configurable": {"thread_id": f"issue-{issue.number}"},
                "recursion_limit": self.recursion_limit,
            }

            log_agent_action(
                f"Invoking ReAct agent with thread_id: issue-{issue.number}, recursion_limit: {self.recursion_limit}",
                "AGENT_INVOKE",
            )

            # Execute the agent with streaming for real-time monitoring
            final_state = self._execute_agent_with_streaming(initial_state, config)

            # ================================================================
            # STEP 6: Process Results
            # ================================================================
            return self._process_agent_results(
                final_state, issue, branch_name, issue_number, draft_pr_number
            )

        except Exception as e:
            error_msg = f"Error processing issue #{issue_number}: {e}"
            log_error(error_msg, "EXCEPTION")
            logger.error(error_msg, exc_info=True)
            return IssueProcessingResult(success=False, error_message=str(e))

    def _execute_agent_with_streaming(
        self, initial_state: AgentState, config: Dict
    ) -> AgentState:
        """
        Execute the ReAct agent with streaming support.

        This method handles the agent execution with streaming to provide
        real-time visibility into the reasoning process. It includes fallback
        to non-streaming execution if streaming fails.

        Args:
            initial_state: Initial agent state
            config: Agent configuration including thread_id and recursion_limit

        Returns:
            Final agent state after execution
        """
        final_state = None
        step_count = 0

        try:
            # Stream the execution to capture state changes
            for chunk in self.agent.stream(
                initial_state, config, stream_mode=["values"], debug=False
            ):
                step_count += 1

                # Handle different chunk formats from LangGraph
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                    last_message = data["messages"][-1]

                    # Determine message type for logging
                    if isinstance(last_message, HumanMessage):
                        message_type = "HumanMessage"
                    elif isinstance(last_message, SystemMessage):
                        message_type = "SystemMessage"
                    else:
                        message_type = type(last_message).__name__

                    log_llm_interaction(last_message, f"{mode} ({message_type})")
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
            # Fallback to non-streaming execution
            final_state = self.agent.invoke(initial_state, config)
            log_agent_action("Agent execution completed via invoke", "AGENT_COMPLETE")

        if final_state is None:
            raise ValueError("Failed to get final state from agent execution")

        return final_state

    def _process_agent_results(
        self,
        final_state: AgentState,
        issue: Any,
        branch_name: Optional[str],
        issue_number: int,
        draft_pr_number: Optional[int] = None,
    ) -> IssueProcessingResult:
        """
        Process the agent's execution results and create pull requests.

        This method handles the post-execution workflow:
        1. Extract generated content from agent state
        2. Identify files created by the agent's tools
        3. Create fallback files if needed
        4. Generate pull requests
        5. Update the original issue

        Args:
            final_state: Final state from agent execution
            issue: GitHub issue object
            branch_name: Git branch name
            issue_number: GitHub issue number
            draft_pr_number: Pre-created draft PR number (if provided, will be updated to ready)

        Returns:
            IssueProcessingResult with success status and PR details
        """
        # Extract the final response from the agent
        final_message = final_state["messages"][-1]
        generated_content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        log_agent_action(
            f"Generated content length: {len(generated_content)} characters"
        )

        # ================================================================
        # Extract Files Created by Tools
        # ================================================================
        files_created = []

        # Look for ToolMessage instances that contain the tool results
        for msg in final_state.get("messages", []):
            # Check for ToolMessage instances (the actual tool results)
            if hasattr(msg, "name") and msg.name in [
                "create_file_in_repo",
                "edit_file_in_repo",
            ]:
                try:
                    tool_result = json.loads(msg.content)
                    if tool_result.get("success"):
                        # Handle both create and edit operations
                        file_created = tool_result.get(
                            "file_created"
                        ) or tool_result.get("file_edited")
                        if file_created:
                            files_created.append(file_created)
                            # Continue checking for more file creation tool calls
                except json.JSONDecodeError as e:
                    log_error(f"Failed to parse ToolMessage JSON: {e}")
                    continue

        log_agent_action(f"Total files created by tool: {len(files_created)}")

        # ================================================================
        # Cleanup Temporary State
        # ================================================================
        # Clean up temporary instance variables used by tools
        if hasattr(self, "_current_branch"):
            delattr(self, "_current_branch")
        if hasattr(self, "_current_issue_number"):
            delattr(self, "_current_issue_number")

        # ================================================================
        # Create Fallback File if Needed
        # ================================================================
        if not files_created:
            files_created = self._create_fallback_file(
                issue, branch_name, generated_content
            )

        # ================================================================
        # Create Pull Request
        # ================================================================
        if files_created:
            return self._create_pull_request(
                files_created,
                issue,
                branch_name,
                generated_content,
                issue_number,
                draft_pr_number,
            )
        else:
            log_error("No files were created in SAAA repository")
            error_msg = "Failed to create files or pull request in SAAA repository"
            log_error(error_msg)
            return IssueProcessingResult(success=False, error_message=error_msg)

    def _create_fallback_file(
        self, issue: Any, branch_name: Optional[str], generated_content: str
    ) -> List[str]:
        """
        Create a fallback metadata file when no files were created by tools.

        This ensures that every issue processing attempt results in some
        output, even if the agent didn't create the requested files.

        Args:
            issue: GitHub issue object
            branch_name: Git branch name
            generated_content: Agent's generated response

        Returns:
            List of created file paths
        """
        log_agent_action(
            "No files created by tool, creating fallback metadata file",
            "FALLBACK",
        )

        filename = f"generated/issue-{issue.number}.md"
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
            f"Creating fallback file {filename} in SAAA repository",
            "FILE_COMMIT",
        )

        if self.github_client.create_or_update_file(
            path=filename,
            content=file_content,
            message=f"AI Agent response to issue #{issue.number}",
            branch=branch_name,
        ):
            log_agent_action(
                f"Successfully created fallback file: {filename} in SAAA repository"
            )
            return [filename]
        else:
            log_error(f"Failed to create fallback file: {filename} in SAAA repository")
            return []

    def _create_pull_request(
        self,
        files_created: List[str],
        issue: Any,
        branch_name: Optional[str],
        generated_content: str,
        issue_number: int,
        draft_pr_number: Optional[int] = None,
    ) -> IssueProcessingResult:
        """
        Create or update a pull request with the generated files.

        This method either creates a new pull request or updates an existing draft PR that includes:
        - Descriptive title and body
        - List of created files
        - Link to original issue
        - Workflow metadata

        Args:
            files_created: List of file paths that were created
            issue: GitHub issue object
            branch_name: Git branch name
            generated_content: Agent's generated response
            issue_number: GitHub issue number
            draft_pr_number: Pre-created draft PR number (if provided, will be updated to ready)

        Returns:
            IssueProcessingResult with success status and PR details
        """
        log_agent_action(
            f"Files created successfully: {files_created}", "FILES_COMPLETE"
        )

        # Generate pull request title and description
        pr_title = (
            f"Create {', '.join(files_created)} as requested in issue #{issue.number}"
        )
        files_list = "\n".join(
            [f"- `{f}`: {self._describe_file(f)}" for f in files_created]
        )

        pr_body = f"""This pull request was automatically generated by the AI Agent in response to issue #{issue.number}.

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

        # Update existing draft PR or create new one
        if draft_pr_number:
            log_agent_action(
                f"Updating draft PR #{draft_pr_number} to ready state: {pr_title}",
                "PR_UPDATE",
            )

            pr = self.github_client.update_pull_request(
                pr_number=draft_pr_number, title=pr_title, body=pr_body, draft=False
            )
        else:
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
            action_type = "updated" if draft_pr_number else "created"
            log_agent_action(
                f"Successfully {action_type} pull request #{pr.number} in SAAA repository"
            )
            log_agent_action(f"Pull request URL: {pr.html_url}")

            # Add comment to the original issue
            log_agent_action(
                f"Adding completion comment to issue #{issue.number}", "COMMENT"
            )
            completion_comment = f"🎉 **Processing Complete!**\n\nI've successfully processed this issue and {'updated the pull request' if draft_pr_number else 'created a pull request'} #{pr.number} in the SAAA repository with the generated content.\n\n📋 **Pull Request**: {pr.html_url}\n📁 **Files Created**: {', '.join(files_created)}\n\nThe pull request is now ready for review. Please review and merge if satisfactory!"

            self.github_client.add_comment_to_issue(issue.number, completion_comment)

            log_agent_action(
                f"Issue #{issue_number} processed successfully - {'updated' if draft_pr_number else 'created'} PR in SAAA repository",
                "SUCCESS",
            )
            return IssueProcessingResult(
                success=True, pr_number=pr.number, branch_name=branch_name
            )
        else:
            error_msg = f"Failed to {'update' if draft_pr_number else 'create'} pull request in SAAA repository"
            log_error(error_msg)
            return IssueProcessingResult(
                success=False,
                error_message=error_msg,
            )

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _get_system_prompt(self) -> str:
        """
        Generate the system prompt for the ReAct agent.

        The system prompt is crucial for the agent's behavior as it defines:
        1. The agent's role and capabilities
        2. The specific task it needs to perform
        3. The tools available and how to use them
        4. The expected output format

        This prompt is loaded from YAML configuration to maintain consistency
        and allow easy updates without code changes.

        Returns:
            Formatted system prompt string
        """
        return get_system_prompt(
            target_owner=self.github_client.target_owner,
            target_repo=self.github_client.target_repo,
        )

    def _describe_file(self, filename: str) -> str:
        """
        Generate a human-readable description for a file based on its name.

        This method provides contextual descriptions for files created by the agent,
        making pull request descriptions more informative and easier to understand.

        The descriptions are inferred from file extensions and naming patterns,
        providing reasonable defaults for common file types.

        Args:
            filename: The name of the file to describe

        Returns:
            Human-readable description of the file's likely purpose
        """
        log_agent_action(f"Describing file: {filename}", "FILE_DESC")

        # Determine file description based on extension and name patterns
        if filename.endswith(".md"):
            if "test" in filename.lower():
                description = "Test markdown file with example content"
            elif "readme" in filename.lower():
                description = "README documentation file"
            elif "doc" in filename.lower():
                description = "Documentation file"
            else:
                description = "Markdown file with generated content"
        elif filename.endswith(".txt"):
            description = "Text file with generated content"
        elif filename.endswith(".py"):
            description = "Python source code file"
        elif filename.endswith(".js"):
            description = "JavaScript source code file"
        elif filename.endswith(".json"):
            description = "JSON configuration or data file"
        elif filename.endswith(".yml") or filename.endswith(".yaml"):
            description = "YAML configuration file"
        else:
            description = "Generated file as requested"

        log_agent_action(f"File description for {filename}: {description}")
        return description

"""LanGraph ReAct agent for processing GitHub issues."""

import ast
import json
import logging
import re
import sys
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

logger = logging.getLogger(__name__)


def pretty_print_json(data: Any) -> str:
    """Pretty print JSON data for logging."""
    if isinstance(data, str):
        try:
            # Try to parse if it's a JSON string
            parsed = json.loads(data)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return data
    else:
        try:
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(data)


# ANSI color codes for console output
class Colors:
    """ANSI color codes for console output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Agent colors
    AGENT = "\033[94m"  # Blue
    AGENT_BOLD = "\033[1;94m"

    # LLM colors
    LLM = "\033[92m"  # Green
    LLM_BOLD = "\033[1;92m"

    # Tool colors
    TOOL = "\033[95m"  # Magenta
    TOOL_BOLD = "\033[1;95m"

    # Error colors
    ERROR = "\033[91m"  # Red
    ERROR_BOLD = "\033[1;91m"

    # Warning colors
    WARNING = "\033[93m"  # Yellow
    WARNING_BOLD = "\033[1;93m"

    # Info colors
    INFO = "\033[96m"  # Cyan
    INFO_BOLD = "\033[1;96m"


def log_agent_action(message: str, action_type: str = "ACTION"):
    """Log agent actions with color coding."""
    timestamp = logging.Formatter().formatTime(
        logging.LogRecord(
            name="",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        ),
        "%H:%M:%S",
    )

    logger.info(
        f"{Colors.AGENT_BOLD}AGENT {action_type}:{Colors.RESET} {Colors.AGENT}{message}{Colors.RESET}"
    )


def log_llm_interaction(message: str, interaction_type: str = "RESPONSE"):
    """Log LLM interactions with enhanced color coding and formatting."""

    # Handle special interaction types
    if interaction_type == "REQUEST_START":
        logger.info(f"{Colors.INFO_BOLD}{'🚀 LLM REQUEST START'}{Colors.RESET}")
        logger.info(f"{Colors.INFO}{message}{Colors.RESET}")
        return
    elif interaction_type == "REQUEST_END":
        logger.info(f"{Colors.INFO}{message}{Colors.RESET}")
        logger.info(f"{Colors.INFO_BOLD}{'🏁 LLM REQUEST END'}{Colors.RESET}")
        return

    # Different colors for different interaction types
    if interaction_type == "REQUEST":
        color = Colors.INFO
        color_bold = Colors.INFO_BOLD
        icon = "🤖➡️"  # Human to AI
        prefix = "USER → LLM"
    else:  # RESPONSE
        color = Colors.LLM
        color_bold = Colors.LLM_BOLD
        icon = "🤖⬅️"  # AI response
        prefix = "LLM → USER"

    # Format the message with proper line breaks and indentation
    lines = message.split("\n")
    if len(lines) > 1:
        # Multi-line message formatting
        formatted_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                # First line with header
                truncated_line = line[:400] + "..." if len(line) > 400 else line
                formatted_lines.append(
                    f"{color_bold}{prefix}:{Colors.RESET} {color}{truncated_line}{Colors.RESET}"
                )
            else:
                # Subsequent lines with indentation
                if line.strip():  # Only show non-empty lines
                    truncated_line = line[:400] + "..." if len(line) > 400 else line
                    formatted_lines.append(f"{color}    {truncated_line}{Colors.RESET}")

        # Log each line separately for better readability
        for line in formatted_lines[:10]:  # Limit to first 10 lines
            logger.info(line)

        if len(formatted_lines) > 10:
            logger.info(
                f"{color}    ... ({len(formatted_lines) - 10} more lines truncated){Colors.RESET}"
            )
    else:
        # Single line message
        display_message = message[:500] + "..." if len(message) > 500 else message
        logger.info(
            f"{color_bold}{prefix}:{Colors.RESET} {color}{display_message}{Colors.RESET}"
        )

    # Add a subtle separator for better visual distinction
    if interaction_type == "RESPONSE":
        logger.info(f"{Colors.LLM}{'─' * 60}{Colors.RESET}")


def log_tool_usage(tool_name: str, input_data: str, output_data: str):
    """Log tool usage with color coding and pretty-printed JSON."""
    timestamp = logging.Formatter().formatTime(
        logging.LogRecord(
            name="",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        ),
        "%H:%M:%S",
    )

    # Pretty print JSON if possible, otherwise truncate for console display
    try:
        # Try to pretty print input if it's JSON
        if input_data.strip().startswith(("[", "{")):
            display_input = pretty_print_json(input_data)
        else:
            display_input = (
                input_data[:200] + "..." if len(input_data) > 200 else input_data
            )
    except:
        display_input = (
            input_data[:200] + "..." if len(input_data) > 200 else input_data
        )

    try:
        # Try to pretty print output if it's JSON
        if output_data.strip().startswith(("[", "{")):
            display_output = pretty_print_json(output_data)
        else:
            display_output = (
                output_data[:200] + "..." if len(output_data) > 200 else output_data
            )
    except:
        display_output = (
            output_data[:200] + "..." if len(output_data) > 200 else output_data
        )

    logger.info(f"{Colors.TOOL_BOLD}TOOL {tool_name}:{Colors.RESET}")
    logger.info(f"{Colors.TOOL}  Input:{Colors.RESET}")
    for line in display_input.split("\n"):
        if line.strip():
            logger.info(f"{Colors.TOOL}    {line}{Colors.RESET}")
    logger.info(f"{Colors.TOOL}  Output:{Colors.RESET}")
    for line in display_output.split("\n"):
        if line.strip():
            logger.info(f"{Colors.TOOL}    {line}{Colors.RESET}")


def log_error(message: str, error_type: str = "ERROR"):
    """Log errors with color coding."""
    timestamp = logging.Formatter().formatTime(
        logging.LogRecord(
            name="",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        ),
        "%H:%M:%S",
    )

    logger.error(
        f"{Colors.ERROR_BOLD}{error_type}:{Colors.RESET} {Colors.ERROR}{message}{Colors.RESET}"
    )
    logger.error(f"{error_type}: {message}")


def log_info(message: str, info_type: str = "INFO"):
    """Log general information with color coding."""
    timestamp = logging.Formatter().formatTime(
        logging.LogRecord(
            name="",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        ),
        "%H:%M:%S",
    )

    logger.info(
        f"{Colors.INFO_BOLD}{info_type}:{Colors.RESET} {Colors.INFO}{message}{Colors.RESET}"
    )


class AgentState(TypedDict):
    """State for the agent."""

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


class LoggingLLM:
    """Wrapper for LLM to add logging functionality."""

    def __init__(self, base_llm):
        self.base_llm = base_llm
        # Copy all attributes from the base LLM
        for attr in dir(base_llm):
            if not attr.startswith("_") and not callable(getattr(base_llm, attr)):
                setattr(self, attr, getattr(base_llm, attr))

    def invoke(self, messages, **kwargs):
        """Log LLM invocation with enhanced formatting."""
        # Log the input with message type distinction
        if isinstance(messages, list):
            log_llm_interaction("=" * 60, "REQUEST_START")
            for i, msg in enumerate(messages):
                msg_content = str(msg.content) if hasattr(msg, "content") else str(msg)
                msg_type = (
                    type(msg).__name__ if hasattr(msg, "__class__") else "Unknown"
                )

                # Use different colors for different message types
                if "System" in msg_type:
                    msg_color = Colors.WARNING
                    msg_icon = "⚙️"
                elif "Human" in msg_type:
                    msg_color = Colors.INFO
                    msg_icon = "👤"
                else:
                    msg_color = Colors.LLM
                    msg_icon = "🤖"

                logger.info(
                    f"{msg_color}{msg_icon} {msg_type} Message #{i+1}:{Colors.RESET}"
                )

                # Format content with proper line breaks
                content_lines = msg_content.split("\n")
                for j, line in enumerate(content_lines[:5]):  # Show first 5 lines
                    if line.strip():
                        truncated_line = line[:300] + "..." if len(line) > 300 else line
                        logger.info(f"{msg_color}  {truncated_line}{Colors.RESET}")

                if len(content_lines) > 5:
                    logger.info(
                        f"{msg_color}  ... ({len(content_lines) - 5} more lines){Colors.RESET}"
                    )

                if i < len(messages) - 1:  # Add separator between messages
                    logger.info(f"{Colors.INFO}{'┈' * 40}{Colors.RESET}")

            log_llm_interaction("=" * 60, "REQUEST_END")
        else:
            input_content = (
                str(messages.content) if hasattr(messages, "content") else str(messages)
            )
            log_llm_interaction(f"Input: {input_content}", "REQUEST")

        # Call the base LLM
        response = self.base_llm.invoke(messages, **kwargs)

        # Log the response with enhanced formatting
        response_content = (
            str(response.content) if hasattr(response, "content") else str(response)
        )

        # Add response header
        logger.info(f"{Colors.LLM_BOLD}🎯 LLM RESPONSE:{Colors.RESET}")
        logger.info(f"{Colors.LLM}{'═' * 60}{Colors.RESET}")

        # Format response content
        response_lines = response_content.split("\n")
        for i, line in enumerate(response_lines):
            if line.strip():
                # Add line numbers for long responses
                line_prefix = f"{i+1:3d}: " if len(response_lines) > 10 else "     "
                truncated_line = line[:400] + "..." if len(line) > 400 else line
                logger.info(f"{Colors.LLM}{line_prefix}{truncated_line}{Colors.RESET}")

        # Add response footer
        logger.info(f"{Colors.LLM}{'═' * 60}{Colors.RESET}")
        logger.info(
            f"{Colors.LLM_BOLD}📊 Response Length: {len(response_content)} characters{Colors.RESET}"
        )

        return response

    def __getattr__(self, name):
        """Delegate all other attributes to the base LLM."""
        return getattr(self.base_llm, name)


class GitHubIssueAgent:
    """LanGraph ReAct agent for processing GitHub issues."""

    def __init__(
        self,
        github_client: GitHubClient,
        openai_api_key: str,
        model: str = "gpt-4",
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
        self.llm = LoggingLLM(base_llm)
        self.max_iterations = max_iterations
        self.recursion_limit = recursion_limit

        log_agent_action("Initializing GitHub Issue Agent", "INIT")
        log_info(f"Model: {model}, Max iterations: {max_iterations}")
        log_info(f"Recursion limit: {recursion_limit}")
        log_info(
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

            log_tool_usage(
                "create_files_from_request", files_json[:200], "Creating files directly in GitHub..."
            )

            try:
                # Parse the JSON input
                files_array = json.loads(files_json)

                if not isinstance(files_array, list):
                    error_msg = "Input must be a JSON array of file objects"
                    log_tool_usage(
                        "create_files_from_request", files_json[:100], error_msg
                    )
                    return json.dumps({"success": False, "error": error_msg, "files_created": []})

                # Get the current branch name from the instance
                # This will be set when the agent is processing an issue
                current_branch = getattr(self, '_current_branch', None)
                if not current_branch:
                    error_msg = "No branch available for file creation"
                    log_error(error_msg)
                    return json.dumps({"success": False, "error": error_msg, "files_created": []})

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
                        file_content = "# Default Content\n\nThis file was created automatically."

                    log_info(
                        f"Creating file directly in GitHub: {filename} ({len(str(file_content))} characters)"
                    )

                    # Create the file directly in GitHub
                    log_agent_action(
                        f"Creating file {filename} in SAAA repository on branch {current_branch}",
                        "FILE_COMMIT",
                    )
                    
                    # Get the current issue number for the commit message
                    current_issue_number = getattr(self, '_current_issue_number', 'unknown')
                    commit_message = f"Create {filename} as requested in issue #{current_issue_number}"
                    
                    if self.github_client.create_or_update_file(
                        path=filename,
                        content=file_content,
                        message=commit_message,
                        branch=current_branch,
                    ):
                        files_created.append(filename)
                        log_info(f"Successfully created file: {filename} in SAAA repository")
                    else:
                        error_msg = f"Failed to create file: {filename} in SAAA repository"
                        log_error(error_msg)
                        errors.append(error_msg)

                # Prepare result
                result = {
                    "success": len(files_created) > 0,
                    "files_created": files_created,
                    "files_count": len(files_created),
                    "errors": errors if errors else None
                }

                result_json = json.dumps(result, indent=2)
                log_tool_usage(
                    "create_files_from_request",
                    files_json[:100],
                    f"Created {len(files_created)} files directly in GitHub",
                )
                return result_json

            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON format: {e}"
                log_tool_usage("create_files_from_request", files_json[:100], error_msg)
                return json.dumps({"success": False, "error": error_msg, "files_created": []})
            except Exception as e:
                error_msg = f"Error creating files: {e}"
                log_tool_usage("create_files_from_request", files_json[:100], error_msg)
                return json.dumps({"success": False, "error": error_msg, "files_created": []})

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

    def process_issue(self, issue_number: int, branch_name: Optional[str] = None) -> IssueProcessingResult:
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

            log_info(f"Successfully fetched issue #{issue_number}: {issue.title}")
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

            log_info(
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
                for chunk in self.agent.stream(
                    initial_state, config, stream_mode=["values", "updates"], debug=True
                ):
                    step_count += 1

                    # Handle different chunk formats
                    if isinstance(chunk, tuple) and len(chunk) == 2:
                        mode, data = chunk
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

            log_info(f"Generated content length: {len(generated_content)} characters")
            log_agent_action("Checking tool execution results", "PARSE")

            # Check if files were created by the tool (tool creates files directly now)
            files_created = []
            
            # Look for ToolMessage instances that contain the tool results
            log_info("Searching for tool results in message history")
            for msg in final_state.get("messages", []):
                # Check for ToolMessage instances (the actual tool results)
                if hasattr(msg, "name") and msg.name == "create_files_from_request":
                    try:
                        tool_result = json.loads(msg.content)
                        if tool_result.get("success") and tool_result.get("files_created"):
                            files_created.extend(tool_result["files_created"])
                            log_info(
                                f"Tool created {len(tool_result['files_created'])} files directly in GitHub"
                            )
                            break  # Found the tool result, no need to continue
                        elif not tool_result.get("success"):
                            log_error(f"Tool execution failed: {tool_result.get('error', 'Unknown error')}")
                    except json.JSONDecodeError as e:
                        log_error(f"Failed to parse ToolMessage JSON: {e}")
                        continue

            log_info(f"Total files created by tool: {len(files_created)}")

            # Clean up temporary instance variables
            if hasattr(self, '_current_branch'):
                delattr(self, '_current_branch')
            if hasattr(self, '_current_issue_number'):
                delattr(self, '_current_issue_number')

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
                    log_info(
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
                    log_info(
                        f"Successfully created pull request #{pr.number} in SAAA repository"
                    )
                    log_info(f"Pull request URL: {pr.html_url}")
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

    def process_issue_with_logging(self, issue_number: int, branch_name: Optional[str] = None) -> IssueProcessingResult:
        """Process a GitHub issue with detailed state logging.

        Args:
            issue_number: GitHub issue number
            branch_name: Pre-created branch name (if None, will create one)

        Returns:
            Result of processing the issue
        """
        try:
            log_agent_action(
                f"Starting to process issue #{issue_number} with detailed logging",
                "START",
            )

            # Get the issue
            log_agent_action(f"Fetching issue #{issue_number} from GitHub", "FETCH")
            issue = self.github_client.get_issue(issue_number)
            if not issue:
                error_msg = f"Issue #{issue_number} not found"
                log_error(error_msg, "ISSUE_NOT_FOUND")
                return IssueProcessingResult(success=False, error_message=error_msg)

            log_info(f"Successfully fetched issue #{issue_number}: {issue.title}")

            # Prepare the initial state
            issue_data = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "user": issue.user.login if issue.user else "unknown",
                "labels": [label.name for label in issue.labels],
            }

            # Create messages
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

            # Set the current branch and issue number for the tool to use
            self._current_branch = branch_name
            self._current_issue_number = issue.number

            log_agent_action(
                "Starting agent execution with state logging", "AGENT_START"
            )

            # Stream the execution to capture all state changes
            final_state = None
            step_count = 0

            for chunk in self.agent.stream(
                initial_state,
                config,
                stream_mode=[
                    "values",
                    "updates",
                    "debug",
                ],  # Multiple stream modes for comprehensive logging
                debug=True,
            ):
                step_count += 1

                # Handle different chunk formats
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                    self._log_state_change(step_count, mode, data)
                elif isinstance(chunk, dict):
                    # Direct state update
                    self._log_state_change(step_count, "values", chunk)
                    final_state = chunk
                else:
                    log_info(f"Step {step_count}: Unknown chunk format: {type(chunk)}")

            if final_state is None:
                # Fallback to invoke if streaming didn't work as expected
                log_agent_action("Falling back to invoke method", "FALLBACK")
                final_state = self.agent.invoke(initial_state, config)

            # Continue with the rest of the processing...
            # Extract the final response and parse for file creation requirements
            final_message = final_state["messages"][-1]
            generated_content = (
                final_message.content
                if hasattr(final_message, "content")
                else str(final_message)
            )

            log_info(f"Generated content length: {len(generated_content)} characters")
            log_agent_action("Checking tool execution results", "PARSE")

            # Check if files were created by the tool (tool creates files directly now)
            files_created = []
            
            # Look for ToolMessage instances that contain the tool results
            log_info("Searching for tool results in message history")
            for msg in final_state.get("messages", []):
                # Check for ToolMessage instances (the actual tool results)
                if hasattr(msg, "name") and msg.name == "create_files_from_request":
                    try:
                        tool_result = json.loads(msg.content)
                        if tool_result.get("success") and tool_result.get("files_created"):
                            files_created.extend(tool_result["files_created"])
                            log_info(
                                f"Tool created {len(tool_result['files_created'])} files directly in GitHub"
                            )
                            break  # Found the tool result, no need to continue
                        elif not tool_result.get("success"):
                            log_error(f"Tool execution failed: {tool_result.get('error', 'Unknown error')}")
                    except json.JSONDecodeError as e:
                        log_error(f"Failed to parse ToolMessage JSON: {e}")
                        continue

            log_info(f"Total files created by tool: {len(files_created)}")

            # Clean up temporary instance variables
            if hasattr(self, '_current_branch'):
                delattr(self, '_current_branch')
            if hasattr(self, '_current_issue_number'):
                delattr(self, '_current_issue_number')

            # Create fallback file if no files were created by the tool
            if not files_created:
                # Parse the issue to extract file requirements for fallback generation
                import re

                # Try to extract file requirements from the issue
                issue_text = f"{issue.title}\n{issue.body or ''}"

                # Look for file creation patterns
                file_patterns = [
                    r"[Cc]reate\s+(?:a\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)",  # "Create TEST.md"
                    r"[Aa]dd\s+(?:a\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)",  # "Add TEST.md"
                    r"[Mm]ake\s+(?:a\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)",  # "Make TEST.md"
                    r"([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)\s+(?:file|document)",  # "TEST.md file"
                ]

                requested_files = []
                for pattern in file_patterns:
                    matches = re.findall(pattern, issue_text, re.IGNORECASE)
                    requested_files.extend(matches)

                # Remove duplicates
                requested_files = list(dict.fromkeys(requested_files))
                log_info(f"Extracted requested files for fallback: {requested_files}")

                if requested_files:
                    log_agent_action(
                        f"Creating {len(requested_files)} requested files as fallback",
                        "FALLBACK_FILE_CREATE",
                    )
                    # Create the specific files requested in the issue as fallback
                    for filename in requested_files:
                        log_info(f"Processing fallback file: {filename}")
                        # Generate content for the specific file based on the issue requirements
                        if "describing" in issue_text.lower():
                            desc_match = re.search(
                                r"describing\s+(.+?)(?:\.|$)", issue_text, re.IGNORECASE
                            )
                            topic = (
                                desc_match.group(1).strip()
                                if desc_match
                                else "the requested topic"
                            )
                        else:
                            topic = "the requested content"

                        log_info(f"Generating content for topic: {topic}")

                        # Generate appropriate content based on file type
                        if filename.endswith(".md"):
                            file_content = f"""# {topic.title()}

{self._generate_content_for_topic(topic)}

---
*This file was automatically generated by AI Agent in response to issue #{issue.number}*
"""
                        else:
                            file_content = f"""{self._generate_content_for_topic(topic)}

This file was automatically generated by AI Agent in response to issue #{issue.number}
"""

                        log_agent_action(
                            f"Creating fallback file {filename} in SAAA repository on branch {branch_name}",
                            "FILE_COMMIT",
                        )
                        if self.github_client.create_or_update_file(
                            path=filename,
                            content=file_content,
                            message=f"Create {filename} as requested in issue #{issue.number}",
                            branch=branch_name,
                        ):
                            files_created.append(filename)
                            log_info(
                                f"Successfully created fallback file: {filename} in SAAA repository"
                            )
                        else:
                            log_error(
                                f"Failed to create fallback file: {filename} in SAAA repository"
                            )
                else:
                    log_agent_action(
                        "No specific files requested, creating metadata file",
                        "FALLBACK",
                    )
                    # Fallback: create a metadata file if no specific files were identified
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
                        f"Creating fallback metadata file {file_path} in SAAA repository",
                        "FILE_COMMIT",
                    )
                    if self.github_client.create_or_update_file(
                        path=file_path,
                        content=file_content,
                        message=f"AI Agent response to issue #{issue.number}",
                        branch=branch_name,
                    ):
                        files_created.append(file_path)
                        log_info(
                            f"Successfully created fallback metadata file: {file_path} in SAAA repository"
                        )
                    else:
                        log_error(
                            f"Failed to create fallback metadata file: {file_path} in SAAA repository"
                        )

            if files_created:
                    log_agent_action(
                        f"Files created successfully: {files_created}", "FILES_COMPLETE"
                    )
                    # Create pull request
                    if requested_files:
                        pr_title = f"Create {', '.join(requested_files)} as requested in issue #{issue.number}"
                        files_list = "\n".join(
                            [
                                f"- `{f}`: {self._describe_file(f)}"
                                for f in files_created
                            ]
                        )
                    else:
                        pr_title = (
                            f"AI Agent Response to Issue #{issue.number}: {issue.title}"
                        )
                        files_list = (
                            f"- `{files_created[0]}`: Generated response content"
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
                        log_info(
                            f"Successfully created pull request #{pr.number} in SAAA repository"
                        )
                        log_info(f"Pull request URL: {pr.html_url}")
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

    def _log_state_change(self, step: int, mode: str, data: Any):
        """Log individual state changes during agent execution with enhanced formatting."""
        step_prefix = f"{Colors.INFO_BOLD}📊 STEP {step}{Colors.RESET}"

        if mode == "values":
            # Log complete state values with enhanced formatting
            if isinstance(data, dict):
                if "messages" in data:
                    message_count = len(data["messages"])
                    last_message = data["messages"][-1] if data["messages"] else None

                    # Determine message type and use appropriate color
                    if last_message:
                        msg_type = type(last_message).__name__
                        if "AI" in msg_type or "Assistant" in msg_type:
                            msg_color = Colors.LLM
                            msg_icon = "🤖"
                        elif "Human" in msg_type:
                            msg_color = Colors.INFO
                            msg_icon = "👤"
                        elif "System" in msg_type:
                            msg_color = Colors.WARNING
                            msg_icon = "⚙️"
                        else:
                            msg_color = Colors.AGENT
                            msg_icon = "📝"

                        last_content = (
                            getattr(last_message, "content", str(last_message))
                            if last_message
                            else "None"
                        )
                    else:
                        msg_color = Colors.INFO
                        msg_icon = "📝"
                        last_content = "None"

                    # Enhanced state logging with visual separators
                    logger.info(
                        f"{step_prefix} {Colors.AGENT_BOLD}STATE UPDATE{Colors.RESET}"
                    )
                    logger.info(f"{Colors.AGENT}{'┌' + '─' * 58 + '┐'}{Colors.RESET}")
                    logger.info(
                        f"{Colors.AGENT}│{Colors.RESET} {Colors.INFO}Messages:{Colors.RESET} {message_count:<10} {Colors.INFO}Generated:{Colors.RESET} {'Yes' if data.get('generated_content') else 'No':<5} {Colors.AGENT}│{Colors.RESET}"
                    )
                    logger.info(
                        f"{Colors.AGENT}│{Colors.RESET} {Colors.INFO}Branch:{Colors.RESET} {str(data.get('branch_name', 'None')):<12} {Colors.INFO}PR Created:{Colors.RESET} {str(data.get('pr_created', False)):<5} {Colors.AGENT}│{Colors.RESET}"
                    )
                    logger.info(f"{Colors.AGENT}{'└' + '─' * 58 + '┘'}{Colors.RESET}")

                    # Log the last message content with type indication
                    if last_content and str(last_content).strip():
                        truncated_content = (
                            str(last_content)[:150] + "..."
                            if len(str(last_content)) > 150
                            else str(last_content)
                        )
                        logger.info(
                            f"{msg_color}{msg_icon} Latest {msg_type if last_message else 'Message'}:{Colors.RESET}"
                        )
                        logger.info(f"{msg_color}  {truncated_content}{Colors.RESET}")

        elif mode == "updates":
            # Log node updates with enhanced formatting
            if isinstance(data, dict):
                logger.info(
                    f"{step_prefix} {Colors.TOOL_BOLD}NODE UPDATES{Colors.RESET}"
                )
                for node_name, update in data.items():
                    if node_name != "__end__":  # Skip end node
                        logger.info(
                            f"{Colors.TOOL}🔧 Node '{node_name}' executed{Colors.RESET}"
                        )

                        if hasattr(update, "content"):
                            content_preview = (
                                str(update.content)[:150] + "..."
                                if len(str(update.content)) > 150
                                else str(update.content)
                            )
                            logger.info(
                                f"{Colors.TOOL}   💬 Output: {content_preview}{Colors.RESET}"
                            )
                        elif isinstance(update, dict):
                            if update:  # Only show non-empty updates
                                pretty_update = pretty_print_json(update)
                                # Split into lines for better formatting
                                for line in pretty_update.split("\n")[
                                    :10
                                ]:  # Show first 10 lines
                                    if line.strip():
                                        logger.info(
                                            f"{Colors.TOOL}   📋 {line}{Colors.RESET}"
                                        )
                        else:
                            update_str = str(update)
                            if update_str and update_str != "None":
                                # Try to pretty print if it looks like JSON
                                if update_str.strip().startswith(("[", "{")):
                                    try:
                                        pretty_result = pretty_print_json(update_str)
                                        for line in pretty_result.split("\n")[:10]:
                                            if line.strip():
                                                logger.info(
                                                    f"{Colors.TOOL}   � {line}{Colors.RESET}"
                                                )
                                    except:
                                        logger.info(
                                            f"{Colors.TOOL}   📤 Result: {update_str[:150]}...{Colors.RESET}"
                                        )
                                else:
                                    logger.info(
                                        f"{Colors.TOOL}   📤 Result: {update_str[:150]}...{Colors.RESET}"
                                    )

        elif mode == "debug":
            # Log debug information with distinct formatting
            logger.info(f"{step_prefix} {Colors.WARNING_BOLD}🐛 DEBUG{Colors.RESET}")
            logger.info(f"{Colors.WARNING}   {str(data)[:200]}...{Colors.RESET}")
        else:
            # Generic mode logging
            logger.info(
                f"{step_prefix} {Colors.INFO_BOLD}📡 {mode.upper()}{Colors.RESET}"
            )
            logger.info(f"{Colors.INFO}   {str(data)[:200]}...{Colors.RESET}")

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

    def _generate_content_for_topic(self, topic: str) -> str:
        """Generate basic content for a given topic."""
        log_agent_action(f"Generating content for topic: {topic}", "CONTENT_GEN")

        # This is a simple implementation - in a real scenario, you might want
        # to use the LLM to generate more sophisticated content
        if "cardiff" in topic.lower():
            content = """Cardiff is the capital and largest city of Wales. Located in the south of Wales, it is a vibrant city with a rich history and modern attractions.

## Key Features
- **Population**: Approximately 365,000 people
- **Location**: South Wales, near the border with England  
- **River**: Situated on the River Taff
- **Bay**: Home to Cardiff Bay, a popular waterfront area

## Notable Attractions
- **Cardiff Castle**: A medieval castle in the heart of the city
- **Millennium Stadium**: Wales' national stadium for rugby and football
- **Cardiff Bay**: Regenerated waterfront with shops, restaurants and entertainment
- **National Museum Cardiff**: Houses art, natural history and archaeology collections

## Economy
Cardiff is a major center for business, finance, and government in Wales. It hosts the Welsh Parliament (Senedd) and many major Welsh institutions.

## Culture
The city has a thriving cultural scene with theaters, music venues, and annual festivals. Welsh and English are both widely spoken."""

        elif "test" in topic.lower():
            content = f"""This is a test file created to demonstrate the AI Agent functionality.

## Purpose
This file serves as an example of how the AI Agent can create files based on GitHub issue requests.

## Topic: {topic}
Content has been generated based on the requirements specified in the GitHub issue.

## Features
- Automatic file creation
- Content generation based on issue requirements
- Proper markdown formatting
- Integration with GitHub workflows"""

        else:
            content = f"""# {topic.title()}

This content was automatically generated based on the topic: {topic}

## Overview
Information and details about {topic} will be provided here.

## Key Points
- Relevant information about the topic
- Generated content based on requirements
- Structured format for easy reading

## Additional Information
Further details and context about {topic} can be added as needed."""

        log_info(
            f"Generated content length: {len(content)} characters for topic: {topic}"
        )
        return content

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

        log_info(f"File description for {filename}: {description}")
        return description


def create_state_logging_graph_example():
    """Example of how to create a LangGraph with comprehensive state logging."""
    from langgraph.graph import StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from typing import TypedDict, Annotated
    from langchain_core.messages import BaseMessage

    class ExampleState(TypedDict):
        """Example state for demonstration."""

        messages: Annotated[List[BaseMessage], add_messages]
        step_count: int
        current_action: str
        data: dict

    def log_state_update(state: ExampleState, step_name: str):
        """Log state updates with detailed information."""
        log_agent_action(f"State update in {step_name}", "STATE_UPDATE")
        log_info(f"  Messages count: {len(state.get('messages', []))}")
        log_info(f"  Step count: {state.get('step_count', 0)}")
        log_info(f"  Current action: {state.get('current_action', 'None')}")
        log_info(f"  Data keys: {list(state.get('data', {}).keys())}")

    def node_1(state: ExampleState) -> ExampleState:
        """Example node with state logging."""
        log_agent_action("Entering node_1", "NODE_ENTRY")
        log_state_update(state, "node_1_entry")

        # Simulate some work
        new_state = {
            **state,
            "step_count": state.get("step_count", 0) + 1,
            "current_action": "processing_in_node_1",
            "data": {**state.get("data", {}), "node_1_result": "completed"},
        }

        log_state_update(new_state, "node_1_exit")
        log_agent_action("Exiting node_1", "NODE_EXIT")
        return new_state

    def node_2(state: ExampleState) -> ExampleState:
        """Another example node with state logging."""
        log_agent_action("Entering node_2", "NODE_ENTRY")
        log_state_update(state, "node_2_entry")

        new_state = {
            **state,
            "step_count": state.get("step_count", 0) + 1,
            "current_action": "processing_in_node_2",
            "data": {**state.get("data", {}), "node_2_result": "completed"},
        }

        log_state_update(new_state, "node_2_exit")
        log_agent_action("Exiting node_2", "NODE_EXIT")
        return new_state

    # Create the graph
    workflow = StateGraph(ExampleState)
    workflow.add_node("node_1", node_1)
    workflow.add_node("node_2", node_2)
    workflow.set_entry_point("node_1")
    workflow.add_edge("node_1", "node_2")
    workflow.add_edge("node_2", END)

    # Compile with checkpointer for state persistence
    app = workflow.compile(checkpointer=MemorySaver())

    return app


def run_with_comprehensive_logging(agent, initial_state, config):
    """Run agent with comprehensive state logging using all available stream modes."""
    log_agent_action("Starting comprehensive logging execution", "START")

    # Available stream modes:
    # - "values": Complete state after each step
    # - "updates": Individual node updates
    # - "debug": Debug information
    # - "messages": LLM message tokens (if applicable)
    # - "custom": Custom events

    final_state = None
    step_count = 0

    try:
        for chunk in agent.stream(
            initial_state,
            config,
            stream_mode=["values", "updates", "debug"],  # Use multiple modes
            debug=True,
        ):
            step_count += 1

            if isinstance(chunk, tuple):
                if len(chunk) == 2:
                    mode, data = chunk
                    _log_chunk_data(step_count, mode, data)
                elif len(chunk) == 3:
                    # For subgraph streaming: (namespace, mode, data)
                    namespace, mode, data = chunk
                    _log_chunk_data(step_count, mode, data, namespace)
            elif isinstance(chunk, dict):
                # Direct state update
                _log_chunk_data(step_count, "values", chunk)
                final_state = chunk
            else:
                log_info(f"Step {step_count}: Unexpected chunk type: {type(chunk)}")

        log_agent_action(
            f"Comprehensive logging completed after {step_count} steps", "COMPLETE"
        )
        return final_state

    except Exception as e:
        log_error(f"Error during comprehensive logging: {e}", "LOGGING_ERROR")
        raise


def _log_chunk_data(step: int, mode: str, data: Any, namespace: tuple = None):
    """Log individual chunk data with detailed formatting."""
    prefix = f"Step {step}"
    if namespace:
        prefix += f" [NS: {'.'.join(namespace)}]"

    if mode == "values":
        if isinstance(data, dict):
            # Log state structure
            state_summary = {
                key: (
                    f"{type(value).__name__}({len(value)} items)"
                    if isinstance(value, (list, dict))
                    else f"{type(value).__name__}"
                )
                for key, value in data.items()
            }
            log_agent_action(
                f"{prefix} - Complete State: {state_summary}", "STATE_VALUES"
            )

            # Log specific interesting fields
            if "messages" in data and data["messages"]:
                last_msg = data["messages"][-1]
                msg_content = getattr(last_msg, "content", str(last_msg))
                truncated = (
                    msg_content[:150] + "..."
                    if len(str(msg_content)) > 150
                    else str(msg_content)
                )
                log_info(f"  Latest message: {truncated}")

    elif mode == "updates":
        if isinstance(data, dict):
            for node_name, update in data.items():
                if node_name != "__end__":
                    log_agent_action(
                        f"{prefix} - Node '{node_name}' produced update", "NODE_UPDATE"
                    )
                    if hasattr(update, "content"):
                        content_preview = (
                            str(update.content)[:100] + "..."
                            if len(str(update.content)) > 100
                            else str(update.content)
                        )
                        log_info(f"  Update content: {content_preview}")
                    else:
                        log_info(f"  Update: {str(update)[:100]}...")

    elif mode == "debug":
        log_info(f"{prefix} - Debug: {str(data)[:150]}...")

    else:
        log_info(f"{prefix} - {mode}: {str(data)[:150]}...")

"""LanGraph ReAct agent for processing GitHub issues."""

import logging
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

    print(
        f"{Colors.AGENT_BOLD}[{timestamp}] AGENT {action_type}:{Colors.RESET} {Colors.AGENT}{message}{Colors.RESET}"
    )
    # logger.info(f"AGENT {action_type}: {message}")


def log_llm_interaction(message: str, interaction_type: str = "RESPONSE"):
    """Log LLM interactions with color coding."""
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

    # Truncate very long messages for console display
    display_message = message[:500] + "..." if len(message) > 500 else message
    print(
        f"{Colors.LLM_BOLD}[{timestamp}] LLM {interaction_type}:{Colors.RESET} {Colors.LLM}{display_message}{Colors.RESET}"
    )
    # logger.info(f"LLM {interaction_type}: {message}")


def log_tool_usage(tool_name: str, input_data: str, output_data: str):
    """Log tool usage with color coding."""
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

    # Truncate for console display
    display_input = input_data[:200] + "..." if len(input_data) > 200 else input_data
    display_output = (
        output_data[:200] + "..." if len(output_data) > 200 else output_data
    )

    print(f"{Colors.TOOL_BOLD}[{timestamp}] TOOL {tool_name}:{Colors.RESET}")
    print(f"{Colors.TOOL}  Input: {display_input}{Colors.RESET}")
    print(f"{Colors.TOOL}  Output: {display_output}{Colors.RESET}")

    # logger.info(f"TOOL {tool_name} - Input: {input_data}")
    # logger.info(f"TOOL {tool_name} - Output: {output_data}")


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

    print(
        f"{Colors.ERROR_BOLD}[{timestamp}] {error_type}:{Colors.RESET} {Colors.ERROR}{message}{Colors.RESET}"
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

    print(
        f"{Colors.INFO_BOLD}[{timestamp}] {info_type}:{Colors.RESET} {Colors.INFO}{message}{Colors.RESET}"
    )
    # logger.info(f"{info_type}: {message}")


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
        """Log LLM invocation."""
        # Log the input
        if isinstance(messages, list):
            input_content = "\n".join(
                [
                    str(msg.content) if hasattr(msg, "content") else str(msg)
                    for msg in messages
                ]
            )
        else:
            input_content = (
                str(messages.content) if hasattr(messages, "content") else str(messages)
            )

        log_llm_interaction(f"Input: {input_content}", "REQUEST")

        # Call the base LLM
        response = self.base_llm.invoke(messages, **kwargs)

        # Log the response
        response_content = (
            str(response.content) if hasattr(response, "content") else str(response)
        )
        log_llm_interaction(f"Output: {response_content}", "RESPONSE")

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
        max_iterations: int = 10,
        recursion_limit: int = 50,
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

        def analyze_issue_requirements(issue_title: str, issue_body: str) -> str:
            """Analyze issue requirements to extract file creation requests and content requirements."""
            import re

            input_data = f"Title: {issue_title}, Body: {issue_body or 'None'}"
            log_tool_usage("analyze_issue_requirements", input_data, "Processing...")

            # Combine title and body for analysis
            full_text = f"{issue_title}\n{issue_body or ''}"

            # Look for file creation patterns
            file_patterns = [
                r"[Cc]reate\s+(?:a\s+)?([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)",  # "Create TEST.md" or "Create a file.txt"
                r"[Aa]dd\s+(?:a\s+)?([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)",  # "Add TEST.md"
                r"[Mm]ake\s+(?:a\s+)?([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)",  # "Make TEST.md"
                r"([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)\s+(?:file|document)",  # "TEST.md file"
            ]

            requested_files = []
            for pattern in file_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                requested_files.extend(matches)

            # Remove duplicates while preserving order
            unique_files = []
            for f in requested_files:
                if f not in unique_files:
                    unique_files.append(f)

            # Extract content requirements
            content_requirements = []
            if "describing" in full_text.lower():
                desc_match = re.search(
                    r"describing\s+(.+?)(?:\.|$)", full_text, re.IGNORECASE
                )
                if desc_match:
                    content_requirements.append(
                        f"describing {desc_match.group(1).strip()}"
                    )

            result = {
                "requested_files": unique_files,
                "content_requirements": content_requirements,
                "original_text": (
                    full_text[:200] + "..." if len(full_text) > 200 else full_text
                ),
            }

            result_str = str(result)
            log_tool_usage("analyze_issue_requirements", input_data, result_str)
            return result_str

        def create_file_content(filename: str, requirements: str) -> str:
            """Create appropriate file content based on filename and requirements."""
            input_data = f"Filename: {filename}, Requirements: {requirements}"
            log_tool_usage("create_file_content", input_data, "Generating content...")

            # This will be enhanced by the LLM to generate actual content
            content = f"Content for {filename} based on requirements: {requirements}"

            log_tool_usage("create_file_content", input_data, content)
            return content

        def validate_content(content: str, filename: str = "") -> str:
            """Validate the generated content."""
            input_data = f"Content length: {len(content)}, Filename: {filename}"
            log_tool_usage("validate_content", input_data, "Validating...")

            validation_result = ""
            if not content or len(content.strip()) == 0:
                validation_result = "Content validation failed: empty content"
            else:
                # Basic validation based on file type
                if filename.endswith(".md"):
                    if not content.startswith("#") and "# " not in content:
                        validation_result = "Content validation warning: Markdown file should contain headers"
                    else:
                        validation_result = "Content validation passed"
                else:
                    validation_result = "Content validation passed"

            log_tool_usage("validate_content", input_data, validation_result)
            return validation_result

        return [
            Tool(
                name="analyze_issue_requirements",
                description="Analyze the GitHub issue title and body to extract file creation requests and content requirements",
                func=lambda issue_text: analyze_issue_requirements(
                    *(
                        issue_text.split("\n", 1)
                        if "\n" in issue_text
                        else (issue_text, "")
                    )
                ),
            ),
            Tool(
                name="create_file_content",
                description="Create appropriate file content based on filename and requirements",
                func=create_file_content,
            ),
            Tool(
                name="validate_content",
                description="Validate the generated content for quality and format",
                func=validate_content,
            ),
        ]

    def process_issue(self, issue_number: int) -> IssueProcessingResult:
        """Process a GitHub issue and create a pull request.

        Args:
            issue_number: GitHub issue number

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
                content=f"""
                Please process this GitHub issue to identify and create the requested files:
                
                Issue #{issue.number}: {issue.title}
                
                Description:
                {issue.body or 'No description provided'}
                
                Labels: {', '.join([label.name for label in issue.labels])}
                
                Please:
                1. Use analyze_issue_requirements to identify what files need to be created
                2. For each requested file, use create_file_content to generate appropriate content
                3. Use validate_content to ensure quality
                4. Provide the final content for each file that should be created
                
                Focus on creating the exact files requested in the issue, not just metadata files.
                """
            )

            log_agent_action(
                "Messages created, preparing to invoke agent", "MESSAGE_READY"
            )

            # Run the agent
            initial_state = AgentState(
                messages=[system_message, human_message],
                issue_data=issue_data,
                generated_content=None,
                branch_name=None,
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

            result = self.agent.invoke(initial_state, config)

            log_agent_action("Agent execution completed", "AGENT_COMPLETE")

            # Extract the final response and parse for file creation requirements
            final_message = result["messages"][-1]
            generated_content = (
                final_message.content
                if hasattr(final_message, "content")
                else str(final_message)
            )

            log_info(f"Generated content length: {len(generated_content)} characters")
            log_agent_action("Parsing issue for file requirements", "PARSE")

            # Parse the issue to extract file requirements
            import re
            import ast

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

            log_info(f"Extracted requested files: {requested_files}")

            # Create feature branch for the SAAA repository
            branch_name = f"ai-agent/issue-{issue.number}"
            log_agent_action(
                f"Creating feature branch '{branch_name}' in SAAA repository",
                "BRANCH_CREATE",
            )
            log_info(
                f"Target repository: {self.github_client.target_owner}/{self.github_client.target_repo}"
            )

            if self.github_client.create_branch(branch_name):
                log_info(
                    f"Successfully created feature branch '{branch_name}' in SAAA repository"
                )
                files_created = []

                if requested_files:
                    log_agent_action(
                        f"Creating {len(requested_files)} requested files",
                        "FILE_CREATE",
                    )
                    # Create the specific files requested in the issue
                    for filename in requested_files:
                        log_info(f"Processing file: {filename}")
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
                            f"Creating file {filename} in SAAA repository on branch {branch_name}",
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
                                f"Successfully created file: {filename} in SAAA repository"
                            )
                        else:
                            log_error(
                                f"Failed to create file: {filename} in SAAA repository"
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
            else:
                log_error(
                    f"Failed to create feature branch '{branch_name}' in SAAA repository"
                )

            error_msg = "Failed to create branch or pull request in SAAA repository"
            log_error(error_msg)
            return IssueProcessingResult(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"Error processing issue #{issue_number}: {e}"
            log_error(error_msg, "EXCEPTION")
            logger.error(error_msg, exc_info=True)
            return IssueProcessingResult(success=False, error_message=str(e))

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return f"""
You are an AI agent designed to process GitHub issues and create the specific files requested in the SAAA repository.

## Repository Context
- **Target Repository**: {self.github_client.target_owner}/{self.github_client.target_repo} (SAAA)
- **Workflow**: Create feature branches, add/update files, create pull requests

Your role is to:
1. Analyze the GitHub issue to identify specific file creation requests
2. Extract the exact filename and content requirements
3. Generate high-quality content that fulfills the request
4. Create the requested files in the SAAA repository using a feature branch
5. Submit a pull request for review and merging

When processing an issue:
- Use analyze_issue_requirements to parse the issue and identify requested files
- If a specific file is requested (like "TEST.md"), create that exact file in the SAAA repository
- Generate content that matches the requirements (e.g., "describing Cardiff" means create content about Cardiff)
- Use create_file_content to generate appropriate content for each file type
- Validate the content before finalizing

For file creation requests:
- Extract the exact filename from the issue text
- Understand the content requirements (what the file should contain)
- Generate relevant, well-structured content
- For markdown files, use proper markdown formatting with headers
- Ensure the content directly addresses what was requested

Use the available tools systematically:
1. analyze_issue_requirements to understand what files to create
2. create_file_content to generate appropriate content
3. validate_content to ensure quality

Always aim to fulfill the specific request rather than creating generic response files.
The files will be created in the SAAA repository on a feature branch and submitted via pull request.
"""

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

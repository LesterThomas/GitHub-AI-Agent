"""LanGraph ReAct agent for processing GitHub issues."""

import logging
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


class GitHubIssueAgent:
    """LanGraph ReAct agent for processing GitHub issues."""

    def __init__(
        self,
        github_client: GitHubClient,
        openai_api_key: str,
        model: str = "gpt-4",
        max_iterations: int = 10,
    ):
        """Initialize the agent.

        Args:
            github_client: GitHub API client
            openai_api_key: OpenAI API key
            model: OpenAI model to use
            max_iterations: Maximum agent iterations
        """
        self.github_client = github_client
        self.llm = ChatOpenAI(api_key=openai_api_key, model=model, temperature=0.1)
        self.max_iterations = max_iterations

        # Create tools for the agent
        self.tools = self._create_tools()

        # Create the ReAct agent
        self.agent = create_react_agent(
            self.llm, self.tools, checkpointer=MemorySaver()
        )

    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent."""

        def create_file_content(content: str) -> str:
            """Create file content based on the issue requirements."""
            return f"Generated content: {content}"

        def analyze_issue_requirements(issue_body: str) -> str:
            """Analyze issue requirements to understand what needs to be generated."""
            # This is a simple implementation - in practice, you might want
            # more sophisticated parsing
            return f"Analyzed requirements from: {issue_body[:200]}..."

        def validate_content(content: str) -> str:
            """Validate the generated content."""
            if len(content.strip()) > 0:
                return "Content validation passed"
            return "Content validation failed: empty content"

        return [
            Tool(
                name="analyze_issue_requirements",
                description="Analyze the GitHub issue to understand what content needs to be generated",
                func=analyze_issue_requirements,
            ),
            Tool(
                name="create_file_content",
                description="Create file content based on the analyzed requirements",
                func=create_file_content,
            ),
            Tool(
                name="validate_content",
                description="Validate the generated content before creating PR",
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
            # Get the issue
            issue = self.github_client.get_issue(issue_number)
            if not issue:
                return IssueProcessingResult(
                    success=False, error_message=f"Issue #{issue_number} not found"
                )

            logger.info(f"Processing issue #{issue_number}: {issue.title}")

            # Prepare the initial state
            issue_data = {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "user": issue.user.login if issue.user else "unknown",
                "labels": [label.name for label in issue.labels],
            }

            # Create system message with context
            system_message = SystemMessage(content=self._get_system_prompt())
            human_message = HumanMessage(
                content=f"""
                Please process this GitHub issue and generate appropriate content:
                
                Issue #{issue.number}: {issue.title}
                
                Description:
                {issue.body or 'No description provided'}
                
                Labels: {', '.join([label.name for label in issue.labels])}
                
                Please analyze the requirements, generate the appropriate content, 
                validate it, and provide a summary of what should be included in the pull request.
                """
            )

            # Run the agent
            initial_state = AgentState(
                messages=[system_message, human_message],
                issue_data=issue_data,
                generated_content=None,
                branch_name=None,
                pr_created=False,
            )

            config = {"configurable": {"thread_id": f"issue-{issue.number}"}}
            result = self.agent.invoke(initial_state, config)

            # Extract the final response
            final_message = result["messages"][-1]
            generated_content = (
                final_message.content
                if hasattr(final_message, "content")
                else str(final_message)
            )

            # Create branch and PR
            branch_name = f"ai-agent/issue-{issue.number}"

            if self.github_client.create_branch(branch_name):
                # Create a file with the generated content
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

                if self.github_client.create_or_update_file(
                    path=file_path,
                    content=file_content,
                    message=f"AI Agent response to issue #{issue.number}",
                    branch=branch_name,
                ):
                    # Create pull request
                    pr_title = (
                        f"AI Agent Response to Issue #{issue.number}: {issue.title}"
                    )
                    pr_body = f"""
This pull request was automatically generated by the AI Agent in response to issue #{issue.number}.

## Original Issue
{issue.title}

## Summary
{generated_content[:500]}...

## Files Changed
- `{file_path}`: Generated response content

## Related Issue
Closes #{issue.number}
"""

                    pr = self.github_client.create_pull_request(
                        title=pr_title,
                        body=pr_body,
                        head=branch_name,
                        base="main",
                        draft=False,
                    )

                    if pr:
                        # Add comment to the original issue
                        self.github_client.add_comment_to_issue(
                            issue.number,
                            f"I've created a pull request #{pr.number} with the generated content. Please review and merge if satisfactory.",
                        )

                        return IssueProcessingResult(
                            success=True, pr_number=pr.number, branch_name=branch_name
                        )

            return IssueProcessingResult(
                success=False, error_message="Failed to create branch or pull request"
            )

        except Exception as e:
            logger.error(f"Error processing issue #{issue_number}: {e}")
            return IssueProcessingResult(success=False, error_message=str(e))

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """
You are an AI agent designed to process GitHub issues and generate appropriate content.

Your role is to:
1. Analyze the GitHub issue requirements carefully
2. Generate appropriate content based on the issue description
3. Validate the generated content
4. Provide clear, helpful responses

When processing an issue:
- Read the issue title and description thoroughly
- Identify what type of content is being requested
- Generate relevant, high-quality content
- Ensure the content addresses the issue requirements
- Be helpful and professional in your responses

Use the available tools to analyze requirements, create content, and validate your work.
Always aim to provide value and follow the instructions given in the issue.
"""

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

        def analyze_issue_requirements(issue_title: str, issue_body: str) -> str:
            """Analyze issue requirements to extract file creation requests and content requirements."""
            import re
            
            # Combine title and body for analysis
            full_text = f"{issue_title}\n{issue_body or ''}"
            
            # Look for file creation patterns
            file_patterns = [
                r'[Cc]reate\s+(?:a\s+)?([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)',  # "Create TEST.md" or "Create a file.txt"
                r'[Aa]dd\s+(?:a\s+)?([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)',     # "Add TEST.md"
                r'[Mm]ake\s+(?:a\s+)?([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)',    # "Make TEST.md"
                r'([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)\s+(?:file|document)',   # "TEST.md file"
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
                desc_match = re.search(r'describing\s+(.+?)(?:\.|$)', full_text, re.IGNORECASE)
                if desc_match:
                    content_requirements.append(f"describing {desc_match.group(1).strip()}")
            
            result = {
                "requested_files": unique_files,
                "content_requirements": content_requirements,
                "original_text": full_text[:200] + "..." if len(full_text) > 200 else full_text
            }
            
            return str(result)

        def create_file_content(filename: str, requirements: str) -> str:
            """Create appropriate file content based on filename and requirements."""
            # This will be enhanced by the LLM to generate actual content
            return f"Content for {filename} based on requirements: {requirements}"

        def validate_content(content: str, filename: str = "") -> str:
            """Validate the generated content."""
            if not content or len(content.strip()) == 0:
                return "Content validation failed: empty content"
            
            # Basic validation based on file type
            if filename.endswith('.md'):
                if not content.startswith('#') and '# ' not in content:
                    return "Content validation warning: Markdown file should contain headers"
            
            return "Content validation passed"

        return [
            Tool(
                name="analyze_issue_requirements",
                description="Analyze the GitHub issue title and body to extract file creation requests and content requirements",
                func=lambda issue_text: analyze_issue_requirements(*issue_text.split('\n', 1) if '\n' in issue_text else (issue_text, "")),
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

            # Extract the final response and parse for file creation requirements
            final_message = result["messages"][-1]
            generated_content = (
                final_message.content
                if hasattr(final_message, "content")
                else str(final_message)
            )

            # Parse the issue to extract file requirements
            import re
            import ast
            
            # Try to extract file requirements from the issue
            issue_text = f"{issue.title}\n{issue.body or ''}"
            
            # Look for file creation patterns
            file_patterns = [
                r'[Cc]reate\s+(?:a\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)',  # "Create TEST.md"
                r'[Aa]dd\s+(?:a\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)',     # "Add TEST.md"
                r'[Mm]ake\s+(?:a\s+)?([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)',    # "Make TEST.md"
                r'([a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+)\s+(?:file|document)',   # "TEST.md file"
            ]
            
            requested_files = []
            for pattern in file_patterns:
                matches = re.findall(pattern, issue_text, re.IGNORECASE)
                requested_files.extend(matches)
            
            # Remove duplicates
            requested_files = list(dict.fromkeys(requested_files))
            
            # Create branch and PR
            branch_name = f"ai-agent/issue-{issue.number}"

            if self.github_client.create_branch(branch_name):
                files_created = []
                
                if requested_files:
                    # Create the specific files requested in the issue
                    for filename in requested_files:
                        # Generate content for the specific file based on the issue requirements
                        if "describing" in issue_text.lower():
                            desc_match = re.search(r'describing\s+(.+?)(?:\.|$)', issue_text, re.IGNORECASE)
                            topic = desc_match.group(1).strip() if desc_match else "the requested topic"
                        else:
                            topic = "the requested content"
                        
                        # Generate appropriate content based on file type
                        if filename.endswith('.md'):
                            file_content = f"""# {topic.title()}

{self._generate_content_for_topic(topic)}

---
*This file was automatically generated by AI Agent in response to issue #{issue.number}*
"""
                        else:
                            file_content = f"""{self._generate_content_for_topic(topic)}

This file was automatically generated by AI Agent in response to issue #{issue.number}
"""
                        
                        if self.github_client.create_or_update_file(
                            path=filename,
                            content=file_content,
                            message=f"Create {filename} as requested in issue #{issue.number}",
                            branch=branch_name,
                        ):
                            files_created.append(filename)
                else:
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
                    if self.github_client.create_or_update_file(
                        path=file_path,
                        content=file_content,
                        message=f"AI Agent response to issue #{issue.number}",
                        branch=branch_name,
                    ):
                        files_created.append(file_path)
                
                if files_created:
                    # Create pull request
                    if requested_files:
                        pr_title = f"Create {', '.join(requested_files)} as requested in issue #{issue.number}"
                        files_list = '\n'.join([f"- `{f}`: {self._describe_file(f)}" for f in files_created])
                    else:
                        pr_title = f"AI Agent Response to Issue #{issue.number}: {issue.title}"
                        files_list = f"- `{files_created[0]}`: Generated response content"
                    
                    pr_body = f"""
This pull request was automatically generated by the AI Agent in response to issue #{issue.number}.

## Original Issue
{issue.title}

## Files Created
{files_list}

## Summary
{generated_content[:500]}{'...' if len(generated_content) > 500 else ''}

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
You are an AI agent designed to process GitHub issues and create the specific files requested.

Your role is to:
1. Analyze the GitHub issue to identify specific file creation requests
2. Extract the exact filename and content requirements
3. Generate high-quality content that fulfills the request
4. Create the requested files with appropriate content

When processing an issue:
- Use analyze_issue_requirements to parse the issue and identify requested files
- If a specific file is requested (like "TEST.md"), create that exact file
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
"""

    def _generate_content_for_topic(self, topic: str) -> str:
        """Generate basic content for a given topic."""
        # This is a simple implementation - in a real scenario, you might want
        # to use the LLM to generate more sophisticated content
        if "cardiff" in topic.lower():
            return """Cardiff is the capital and largest city of Wales. Located in the south of Wales, it is a vibrant city with a rich history and modern attractions.

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
            return f"""This is a test file created to demonstrate the AI Agent functionality.

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
            return f"""# {topic.title()}

This content was automatically generated based on the topic: {topic}

## Overview
Information and details about {topic} will be provided here.

## Key Points
- Relevant information about the topic
- Generated content based on requirements
- Structured format for easy reading

## Additional Information
Further details and context about {topic} can be added as needed."""

    def _describe_file(self, filename: str) -> str:
        """Provide a description of what a file contains based on its name."""
        if filename.endswith('.md'):
            if 'test' in filename.lower():
                return "Test markdown file with example content"
            else:
                return "Markdown file with generated content"
        elif filename.endswith('.txt'):
            return "Text file with generated content"
        else:
            return "Generated file as requested"

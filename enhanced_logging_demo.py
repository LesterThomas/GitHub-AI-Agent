"""
Enhanced LLM Logging Demo

This file demonstrates the improved logging format with proper colors and formatting
for different actors in the LangGraph system.
"""

import logging
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Set up logging to see the colored output
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# ANSI color codes (same as in agent.py)
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


def demo_enhanced_llm_logging():
    """Demonstrate the enhanced LLM logging with different message types."""

    # Sample messages representing different actors
    messages = [
        SystemMessage(
            content="""You are an AI agent designed to process GitHub issues and create the specific files requested in the SAAA repository.

## Repository Context
- **Target Repository**: owner/repo (SAAA)
- **Workflow**: Create feature branches, add/update files, create pull requests

Your role is to:
1. Analyze the GitHub issue to identify specific file creation requests
2. Extract the exact filename and content requirements
3. Generate high-quality content that fulfills the request"""
        ),
        HumanMessage(
            content="""Please process this GitHub issue to identify and create the requested files:

Issue #123: Create TEST.md describing Cardiff

Description:
Please create a TEST.md file describing Cardiff, the capital city of Wales.

Labels: enhancement, documentation

Please:
1. Use analyze_issue_requirements to identify what files need to be created
2. For each requested file, use create_file_content to generate appropriate content
3. Use validate_content to ensure quality
4. Provide the final content for each file that should be created"""
        ),
        AIMessage(
            content="""I'll help you process this GitHub issue to create the requested TEST.md file describing Cardiff. Let me start by analyzing the requirements.

I need to:
1. Analyze the issue requirements to extract file creation requests
2. Create content for TEST.md describing Cardiff
3. Validate the content quality

Let me use the available tools to accomplish this."""
        ),
    ]

    print(f"{Colors.AGENT_BOLD}🚀 ENHANCED LLM LOGGING DEMONSTRATION{Colors.RESET}")
    print(f"{Colors.INFO}{'=' * 80}{Colors.RESET}")

    # Demonstrate the enhanced request logging
    print(f"{Colors.INFO_BOLD}🚀 LLM REQUEST START{Colors.RESET}")
    print(f"{Colors.INFO}{'=' * 60}{Colors.RESET}")

    for i, msg in enumerate(messages):
        msg_content = str(msg.content)
        msg_type = type(msg).__name__

        # Use different colors for different message types
        if "System" in msg_type:
            msg_color = Colors.WARNING
            msg_icon = "⚙️"
        elif "Human" in msg_type:
            msg_color = Colors.INFO
            msg_icon = "👤"
        elif "AI" in msg_type or "Assistant" in msg_type:
            msg_color = Colors.LLM
            msg_icon = "🤖"
        else:
            msg_color = Colors.AGENT
            msg_icon = "📝"

        print(f"{msg_color}{msg_icon} {msg_type} Message #{i+1}:{Colors.RESET}")

        # Format content with proper line breaks
        content_lines = msg_content.split("\n")
        for j, line in enumerate(content_lines[:8]):  # Show first 8 lines
            if line.strip():
                truncated_line = line[:300] + "..." if len(line) > 300 else line
                print(f"{msg_color}  {truncated_line}{Colors.RESET}")

        if len(content_lines) > 8:
            print(
                f"{msg_color}  ... ({len(content_lines) - 8} more lines){Colors.RESET}"
            )

        if i < len(messages) - 1:  # Add separator between messages
            print(f"{Colors.INFO}{'┈' * 40}{Colors.RESET}")

    print(f"{Colors.INFO}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.INFO_BOLD}🏁 LLM REQUEST END{Colors.RESET}")

    # Demonstrate enhanced response logging
    sample_response = """I've analyzed the GitHub issue and identified the requirements. Here's what I found:

**File Creation Request:**
- Filename: TEST.md
- Content requirement: describing Cardiff

**Analysis Results:**
The issue requests creation of a TEST.md file with content describing Cardiff, the capital city of Wales.

**Generated Content for TEST.md:**

# Cardiff

Cardiff is the capital and largest city of Wales. Located in the south of Wales, it is a vibrant city with a rich history and modern attractions.

## Key Features
- **Population**: Approximately 365,000 people
- **Location**: South Wales, near the border with England  
- **River**: Situated on the River Taff
- **Bay**: Home to Cardiff Bay, a popular waterfront area

## Notable Attractions
- **Cardiff Castle**: A medieval castle in the heart of the city
- **Millennium Stadium**: Wales' national stadium for rugby and football

This content fulfills the requirements specified in the GitHub issue."""

    print(f"\n{Colors.LLM_BOLD}🎯 LLM RESPONSE:{Colors.RESET}")
    print(f"{Colors.LLM}{'═' * 60}{Colors.RESET}")

    # Format response content
    response_lines = sample_response.split("\n")
    for i, line in enumerate(response_lines):
        if line.strip():
            # Add line numbers for long responses
            line_prefix = f"{i+1:3d}: " if len(response_lines) > 10 else "     "
            truncated_line = line[:400] + "..." if len(line) > 400 else line
            print(f"{Colors.LLM}{line_prefix}{truncated_line}{Colors.RESET}")

    print(f"{Colors.LLM}{'═' * 60}{Colors.RESET}")
    print(
        f"{Colors.LLM_BOLD}📊 Response Length: {len(sample_response)} characters{Colors.RESET}"
    )
    print(f"{Colors.LLM}{'─' * 60}{Colors.RESET}")


def demo_state_change_logging():
    """Demonstrate enhanced state change logging."""

    print(f"\n{Colors.AGENT_BOLD}📊 STATE CHANGE LOGGING DEMONSTRATION{Colors.RESET}")
    print(f"{Colors.INFO}{'=' * 80}{Colors.RESET}")

    # Sample state data
    sample_state = {
        "messages": [
            SystemMessage(content="System initialized"),
            HumanMessage(content="Create TEST.md describing Cardiff"),
            AIMessage(content="I'll create the TEST.md file as requested..."),
        ],
        "issue_data": {"number": 123, "title": "Create TEST.md describing Cardiff"},
        "generated_content": "# Cardiff\n\nCardiff is the capital...",
        "branch_name": "ai-agent/issue-123",
        "pr_created": False,
    }

    step = 3
    step_prefix = f"{Colors.INFO_BOLD}📊 STEP {step}{Colors.RESET}"

    # Enhanced state logging with visual separators
    print(f"{step_prefix} {Colors.AGENT_BOLD}STATE UPDATE{Colors.RESET}")
    print(f"{Colors.AGENT}{'┌' + '─' * 58 + '┐'}{Colors.RESET}")
    print(
        f"{Colors.AGENT}│{Colors.RESET} {Colors.INFO}Messages:{Colors.RESET} {len(sample_state['messages']):<10} {Colors.INFO}Generated:{Colors.RESET} {'Yes':<5} {Colors.AGENT}│{Colors.RESET}"
    )
    print(
        f"{Colors.AGENT}│{Colors.RESET} {Colors.INFO}Branch:{Colors.RESET} {sample_state['branch_name']:<12} {Colors.INFO}PR Created:{Colors.RESET} {'False':<5} {Colors.AGENT}│{Colors.RESET}"
    )
    print(f"{Colors.AGENT}{'└' + '─' * 58 + '┘'}{Colors.RESET}")

    # Show last message with actor-specific colors
    last_message = sample_state["messages"][-1]
    msg_type = type(last_message).__name__
    msg_color = Colors.LLM
    msg_icon = "🤖"

    last_content = getattr(last_message, "content", str(last_message))
    truncated_content = (
        last_content[:150] + "..."
        if len(str(last_content)) > 150
        else str(last_content)
    )
    print(f"{msg_color}{msg_icon} Latest {msg_type}:{Colors.RESET}")
    print(f"{msg_color}  {truncated_content}{Colors.RESET}")


def demo_tool_execution_logging():
    """Demonstrate enhanced tool execution logging."""

    print(f"\n{Colors.TOOL_BOLD}🔧 TOOL EXECUTION LOGGING DEMONSTRATION{Colors.RESET}")
    print(f"{Colors.INFO}{'=' * 80}{Colors.RESET}")

    step = 2
    step_prefix = f"{Colors.INFO_BOLD}📊 STEP {step}{Colors.RESET}"

    # Sample tool updates
    tool_updates = {
        "analyze_issue_requirements": "Identified file: TEST.md, requirement: describing Cardiff",
        "create_file_content": "Generated markdown content for Cardiff description",
        "validate_content": "Content validation passed - proper markdown formatting detected",
    }

    print(f"{step_prefix} {Colors.TOOL_BOLD}NODE UPDATES{Colors.RESET}")
    for tool_name, update in tool_updates.items():
        print(f"{Colors.TOOL}🔧 Node '{tool_name}' executed{Colors.RESET}")
        content_preview = update[:150] + "..." if len(update) > 150 else update
        print(f"{Colors.TOOL}   💬 Output: {content_preview}{Colors.RESET}")


if __name__ == "__main__":
    demo_enhanced_llm_logging()
    demo_state_change_logging()
    demo_tool_execution_logging()

    print(f"\n{Colors.AGENT_BOLD}✨ LOGGING ENHANCEMENT SUMMARY{Colors.RESET}")
    print(f"{Colors.INFO}{'=' * 80}{Colors.RESET}")
    print(
        f"{Colors.WARNING}⚙️  System Messages:{Colors.RESET} {Colors.WARNING}Yellow/Orange{Colors.RESET}"
    )
    print(
        f"{Colors.INFO}👤 Human Messages:{Colors.RESET} {Colors.INFO}Cyan{Colors.RESET}"
    )
    print(f"{Colors.LLM}🤖 AI Messages:{Colors.RESET} {Colors.LLM}Green{Colors.RESET}")
    print(
        f"{Colors.AGENT}📊 State Updates:{Colors.RESET} {Colors.AGENT}Blue{Colors.RESET}"
    )
    print(
        f"{Colors.TOOL}🔧 Tool Execution:{Colors.RESET} {Colors.TOOL}Magenta{Colors.RESET}"
    )
    print(
        f"{Colors.ERROR}❌ Error Messages:{Colors.RESET} {Colors.ERROR}Red{Colors.RESET}"
    )
    print(f"{Colors.INFO}{'=' * 80}{Colors.RESET}")

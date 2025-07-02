"""Enhanced logging utilities with color support."""

import json
from datetime import datetime
from typing import Any


# ANSI color codes for console output
class Colors:
    """ANSI color codes for console output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Modern color palette
    AGENT = "\033[38;5;45m"  # Bright cyan
    AGENT_BOLD = "\033[1;38;5;45m"

    LLM = "\033[38;5;10m"  # Bright green
    LLM_BOLD = "\033[1;38;5;10m"

    TOOL = "\033[38;5;213m"  # Pink/magenta
    TOOL_BOLD = "\033[1;38;5;213m"

    SUCCESS = "\033[38;5;46m"  # Bright green
    SUCCESS_BOLD = "\033[1;38;5;46m"

    ERROR = "\033[38;5;196m"  # Bright red
    ERROR_BOLD = "\033[1;38;5;196m"

    WARNING = "\033[38;5;214m"  # Orange
    WARNING_BOLD = "\033[1;38;5;214m"

    INFO = "\033[38;5;117m"  # Light blue
    INFO_BOLD = "\033[1;38;5;117m"

    GITHUB = "\033[38;5;208m"  # Orange
    GITHUB_BOLD = "\033[1;38;5;208m"

    # UI Elements
    BORDER = "\033[38;5;240m"  # Dark gray
    SEPARATOR = "─"
    ARROW = "→"
    BULLET = "•"


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


def get_timestamp():
    """Get a formatted timestamp."""
    return datetime.now().strftime("%H:%M:%S")


def print_separator(char="─", length=80, color=None):
    """Print a visual separator line."""
    if color:
        print(f"{color}{char * length}{Colors.RESET}")
    else:
        print(f"{Colors.BORDER}{char * length}{Colors.RESET}")


def log_agent_action(message: str, action_type: str = "ACTION"):
    """Log agent actions with enhanced formatting and color coding."""
    timestamp = get_timestamp()

    # Special handling for different action types
    icon_map = {
        "APP_START": "🚀",
        "APP_INIT": "⚙️",
        "CLIENT_INIT": "🔗",
        "AGENT_INIT": "🤖",
        "POLL": "👀",
        "NEW_ISSUES": "📝",
        "ISSUE_START": "🎯",
        "BRANCH_CREATE_EARLY": "🌿",
        "SUCCESS": "✅",
        "FAILED": "❌",
        "ERROR": "💥",
        "COMPLETE": "🏁",
        "MODE": "⚡",
        "RUN_ONCE": "▶️",
        "DAEMON_START": "🔄",
        "SHUTDOWN": "🛑",
    }

    icon = icon_map.get(action_type, "🔹")

    # Format based on action importance
    if action_type in ["SUCCESS", "COMPLETE"]:
        color = Colors.SUCCESS_BOLD
        border_color = Colors.SUCCESS
    elif action_type in ["ERROR", "FAILED"]:
        color = Colors.ERROR_BOLD
        border_color = Colors.ERROR
    elif action_type in ["APP_START", "APP_INIT", "ISSUE_START"]:
        color = Colors.AGENT_BOLD
        border_color = Colors.AGENT
    else:
        color = Colors.AGENT
        border_color = Colors.AGENT

    # Print formatted message
    print(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} {icon} {color}{message}{Colors.RESET}"
    )


def log_github_action(message: str, action_type: str = "GITHUB"):
    """Log GitHub-specific actions."""
    timestamp = get_timestamp()
    icon = "🐙"  # GitHub octopus

    print(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} {icon} {Colors.GITHUB}{message}{Colors.RESET}"
    )


def log_llm_interaction(message: str, interaction_type: str = "RESPONSE"):
    """Log LLM interactions with clean, readable formatting."""
    timestamp = get_timestamp()

    if interaction_type == "REQUEST":
        icon = "🧠➡️"
        color = Colors.INFO
        label = "AI REQUEST"
    elif interaction_type == "RESPONSE":
        icon = "🧠⬅️"
        color = Colors.LLM
        label = "AI RESPONSE"
    elif interaction_type == "THINKING":
        icon = "🤔"
        color = Colors.LLM_BOLD
        label = "AI THINKING"
    else:
        icon = "🧠"
        color = Colors.LLM
        label = "AI"

    # Truncate long messages for readability
    display_message = message
    if len(message) > 150:
        display_message = message[:147] + "..."

    print(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} {icon} {color}{display_message}{Colors.RESET}"
    )


def log_tool_usage(tool_name: str, input_data: str, output_data: str):
    """Log tool usage with clean, formatted output."""
    timestamp = get_timestamp()
    icon = "🔧"

    print(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} {icon} {Colors.TOOL_BOLD}TOOL {tool_name}{Colors.RESET}"
    )

    # Show truncated input/output for readability
    if input_data:
        truncated_input = (
            input_data[:100] + "..." if len(input_data) > 100 else input_data
        )
        print(f"   {Colors.TOOL}└─ Input: {truncated_input}{Colors.RESET}")

    if output_data:
        truncated_output = (
            output_data[:100] + "..." if len(output_data) > 100 else output_data
        )
        if "success" in output_data.lower() and "true" in output_data.lower():
            print(f"   {Colors.SUCCESS}└─ ✅ {truncated_output}{Colors.RESET}")
        elif "error" in output_data.lower() or "failed" in output_data.lower():
            print(f"   {Colors.ERROR}└─ ❌ {truncated_output}{Colors.RESET}")
        else:
            print(f"   {Colors.TOOL}└─ Output: {truncated_output}{Colors.RESET}")


def log_error(message: str, error_type: str = "ERROR"):
    """Log errors with prominent formatting."""
    timestamp = get_timestamp()
    icon = "💥" if error_type == "ERROR" else "⚠️"

    print(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} {icon} {Colors.ERROR_BOLD}{message}{Colors.RESET}"
    )


def log_info(message: str, info_type: str = "INFO"):
    """Log general information with clean formatting."""
    timestamp = get_timestamp()

    # Choose appropriate icon and color based on content
    if "successfully" in message.lower() or "created" in message.lower():
        icon = "✅"
        color = Colors.SUCCESS
    elif "repository" in message.lower() or "github" in message.lower():
        icon = "🐙"
        color = Colors.GITHUB
    elif "file" in message.lower():
        icon = "📄"
        color = Colors.INFO
    else:
        icon = "ℹ️"
        color = Colors.INFO

    print(
        f"{Colors.DIM}[{timestamp}]{Colors.RESET} {icon} {color}{message}{Colors.RESET}"
    )


def log_section_start(title: str):
    """Log the start of a major section with visual emphasis."""
    print_separator("═", 60, Colors.AGENT)
    print(f"{Colors.AGENT_BOLD}🎯 {title.upper()}{Colors.RESET}")
    print_separator("─", 60, Colors.AGENT)

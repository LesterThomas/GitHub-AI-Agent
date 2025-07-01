#!/usr/bin/env python3
"""
Test script to demonstrate the color-coded logging functionality.
Run this to see how the logging looks in action without processing real issues.
"""

import logging
import sys
import time
from github_ai_agent.agent import (
    log_agent_action,
    log_llm_interaction,
    log_tool_usage,
    log_error,
    log_info,
    Colors,
)


def demo_logging():
    """Demonstrate all the different types of logging."""

    print(f"{Colors.INFO_BOLD}=== GitHub AI Agent Logging Demo ==={Colors.RESET}\n")

    # Agent actions
    log_agent_action("Initializing GitHub Issue Agent", "INIT")
    time.sleep(0.5)

    log_agent_action("Starting to process issue #123", "START")
    time.sleep(0.5)

    log_agent_action("Fetching issue #123 from GitHub", "FETCH")
    time.sleep(0.5)

    # Info messages
    log_info("Successfully fetched issue #123: Create TEST.md describing Cardiff")
    log_info(
        "Issue data prepared: Create TEST.md describing Cardiff, User: testuser, Labels: ['ai-agent']"
    )
    log_info("Model: gpt-4o-mini, Max iterations: 20")
    log_info("Recursion limit: 50")
    time.sleep(0.5)

    # Tool usage
    log_tool_usage(
        "analyze_issue_requirements",
        "Title: Create TEST.md describing Cardiff, Body: Please create a TEST.md file describing Cardiff",
        "{'requested_files': ['TEST.md'], 'content_requirements': ['describing Cardiff']}",
    )
    time.sleep(0.5)

    # LLM interactions
    log_llm_interaction(
        "Analyze this GitHub issue and identify what files need to be created...",
        "REQUEST",
    )
    time.sleep(0.5)

    log_llm_interaction(
        "I need to create a TEST.md file with content about Cardiff. Let me use the analyze_issue_requirements tool first...",
        "RESPONSE",
    )
    time.sleep(0.5)

    # More tool usage
    log_tool_usage(
        "create_file_content",
        "Filename: TEST.md, Requirements: describing Cardiff",
        "# Cardiff\n\nCardiff is the capital and largest city of Wales...",
    )
    time.sleep(0.5)

    log_tool_usage(
        "validate_content",
        "Content length: 1247, Filename: TEST.md",
        "Content validation passed",
    )
    time.sleep(0.5)

    # Agent actions for file creation
    log_agent_action(
        "Creating feature branch 'ai-agent/issue-123' in SAAA repository",
        "BRANCH_CREATE",
    )
    log_info("Target repository: LesterThomas/SAAA")
    log_info(
        "Successfully created feature branch 'ai-agent/issue-123' in SAAA repository"
    )
    time.sleep(0.5)

    log_agent_action("Creating 1 requested files", "FILE_CREATE")
    log_info("Processing file: TEST.md")
    log_info("Generating content for topic: Cardiff")
    time.sleep(0.5)

    log_agent_action(
        "Creating file TEST.md in SAAA repository on branch ai-agent/issue-123",
        "FILE_COMMIT",
    )
    log_info("Successfully created file: TEST.md in SAAA repository")
    time.sleep(0.5)

    # PR creation
    log_agent_action("Files created successfully: ['TEST.md']", "FILES_COMPLETE")
    log_agent_action(
        "Creating pull request to SAAA repository: Create TEST.md as requested in issue #123",
        "PR_CREATE",
    )
    log_info("Successfully created pull request #45 in SAAA repository")
    log_info("Pull request URL: https://github.com/LesterThomas/SAAA/pull/45")
    time.sleep(0.5)

    log_agent_action("Adding comment to issue #123", "COMMENT")
    log_agent_action(
        "Issue #123 processed successfully - created PR in SAAA repository", "SUCCESS"
    )
    time.sleep(0.5)

    # Show some error examples
    print(f"\n{Colors.WARNING_BOLD}=== Error Examples ==={Colors.RESET}\n")

    log_error("Failed to create file: invalid-file.txt", "FILE_ERROR")
    log_error("Issue #999 not found", "ISSUE_NOT_FOUND")
    log_error("Error processing issue #123: Connection timeout", "EXCEPTION")

    print(f"\n{Colors.INFO_BOLD}=== Demo Complete ==={Colors.RESET}")
    print(
        f"{Colors.INFO}This demonstrates how all agent, LLM, and tool interactions are logged with color coding.{Colors.RESET}"
    )
    print(
        f"{Colors.INFO}Colors: {Colors.AGENT}Agent (Blue){Colors.RESET}, {Colors.LLM}LLM (Green){Colors.RESET}, {Colors.TOOL}Tools (Magenta){Colors.RESET}, {Colors.ERROR}Errors (Red){Colors.RESET}"
    )


if __name__ == "__main__":
    demo_logging()

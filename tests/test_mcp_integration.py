"""Integration test demonstrating MCP tools with the GitHub AI Agent."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from github_ai_agent.agent import GitHubIssueAgent
from github_ai_agent.github_client import GitHubClient
from github_ai_agent.mcp_client import MCPClient


def test_agent_with_mcp_tools():
    """Test that the agent can be initialized with MCP tools."""
    # Create a temporary MCP config file
    config_data = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_config = f.name

    try:
        # Mock GitHub client
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.target_owner = "test_owner"
        mock_github_client.target_repo = "test_repo"

        # Create agent with MCP enabled
        agent = GitHubIssueAgent(
            github_client=mock_github_client,
            openai_api_key="test_key",
            model="gpt-4o-mini",
            mcp_config_file=temp_config,
            enable_mcp=True,
        )

        # Check that MCP tools are loaded
        tool_names = [tool.name for tool in agent.tools]

        # Should have both repository tools and MCP tools
        repo_tools = [
            name
            for name in tool_names
            if name.startswith(
                ("create_file", "read_file", "list_files", "edit_file", "delete_file")
            )
        ]
        mcp_tools = [name for name in tool_names if name.startswith("mcp_")]

        assert len(repo_tools) == 5  # 5 repository tools
        assert len(mcp_tools) >= 3  # At least 3 MCP filesystem tools

        # Verify specific MCP tools exist
        assert any("mcp_filesystem_read_file" in name for name in tool_names)
        assert any("mcp_filesystem_write_file" in name for name in tool_names)
        assert any("mcp_filesystem_list_directory" in name for name in tool_names)

        # Test cleanup
        agent.cleanup()

    finally:
        Path(temp_config).unlink()


def test_agent_without_mcp():
    """Test that the agent works correctly when MCP is disabled."""
    # Mock GitHub client
    mock_github_client = Mock(spec=GitHubClient)
    mock_github_client.target_owner = "test_owner"
    mock_github_client.target_repo = "test_repo"

    # Create agent with MCP disabled
    agent = GitHubIssueAgent(
        github_client=mock_github_client,
        openai_api_key="test_key",
        model="gpt-4o-mini",
        enable_mcp=False,
    )

    # Check that only repository tools are loaded
    tool_names = [tool.name for tool in agent.tools]

    repo_tools = [
        name
        for name in tool_names
        if name.startswith(
            ("create_file", "read_file", "list_files", "edit_file", "delete_file")
        )
    ]
    mcp_tools = [name for name in tool_names if name.startswith("mcp_")]

    assert len(repo_tools) == 5  # 5 repository tools
    assert len(mcp_tools) == 0  # No MCP tools

    # Test cleanup (should not fail even without MCP)
    agent.cleanup()


def test_mcp_tool_execution():
    """Test that MCP tools can be executed through the agent."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test file content")
        temp_file = f.name

    try:
        # Create MCP client directly
        mcp_client = MCPClient()

        # Test read_file tool
        result = mcp_client.call_tool("read_file", "filesystem", {"path": temp_file})
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["content"] == "Test file content"

        # Test write_file tool
        new_content = "Updated content"
        result = mcp_client.call_tool(
            "write_file", "filesystem", {"path": temp_file, "content": new_content}
        )
        result_data = json.loads(result)

        assert result_data["success"] is True

        # Verify the file was updated
        with open(temp_file, "r") as f:
            content = f.read()
        assert content == new_content

    finally:
        Path(temp_file).unlink()


@patch("subprocess.Popen")
def test_mcp_server_lifecycle(mock_popen):
    """Test MCP server startup and shutdown lifecycle."""
    mock_process = Mock()
    mock_popen.return_value = mock_process

    # Create a temporary MCP config file
    config_data = {
        "mcpServers": {
            "test_server": {"command": "npx", "args": ["-y", "test-package"]}
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_config = f.name

    try:
        # Mock GitHub client
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.target_owner = "test_owner"
        mock_github_client.target_repo = "test_repo"

        # Create agent (this should start MCP servers)
        agent = GitHubIssueAgent(
            github_client=mock_github_client,
            openai_api_key="test_key",
            mcp_config_file=temp_config,
            enable_mcp=True,
        )

        # Verify server was started
        mock_popen.assert_called()

        # Cleanup (this should stop MCP servers)
        agent.cleanup()

        # Verify server was stopped
        mock_process.terminate.assert_called()

    finally:
        Path(temp_config).unlink()

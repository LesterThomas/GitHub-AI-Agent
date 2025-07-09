"""Tests for MCP client functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from github_ai_agent.mcp_client import MCPClient, MCPServerConfig, MCPTool


def test_mcp_server_config_creation():
    """Test that MCPServerConfig can be created correctly."""
    config = MCPServerConfig(
        name="test_server",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        env={"TEST_VAR": "test_value"},
    )

    assert config.name == "test_server"
    assert config.command == "npx"
    assert config.args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    assert config.env == {"TEST_VAR": "test_value"}


def test_mcp_tool_creation():
    """Test that MCPTool can be created correctly."""
    tool = MCPTool(
        name="read_file",
        description="Read a file from the filesystem",
        server_name="filesystem",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"}
            },
            "required": ["path"],
        },
    )

    assert tool.name == "read_file"
    assert tool.description == "Read a file from the filesystem"
    assert tool.server_name == "filesystem"
    assert "path" in tool.input_schema["properties"]


def test_mcp_client_initialization():
    """Test that MCPClient can be initialized."""
    client = MCPClient("test_config.json")
    assert client.config_file == "test_config.json"
    assert client.server_configs == {}
    assert client.available_tools == []
    assert client.server_processes == {}


def test_load_config_with_valid_file():
    """Test loading MCP configuration from a valid JSON file."""
    config_data = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"TEST_VAR": "value"},
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "workingDirectory": "/app",
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_file = f.name

    try:
        client = MCPClient(temp_file)
        client.load_config()

        assert len(client.server_configs) == 2
        assert "filesystem" in client.server_configs
        assert "github" in client.server_configs

        fs_config = client.server_configs["filesystem"]
        assert fs_config.name == "filesystem"
        assert fs_config.command == "npx"
        assert fs_config.env == {"TEST_VAR": "value"}

        gh_config = client.server_configs["github"]
        assert gh_config.name == "github"
        assert gh_config.working_directory == "/app"

    finally:
        Path(temp_file).unlink()


def test_load_config_with_missing_file():
    """Test loading MCP configuration when file doesn't exist."""
    client = MCPClient("nonexistent_file.json")
    client.load_config()

    # Should not raise an exception, just log a warning
    assert len(client.server_configs) == 0


def test_discover_tools_filesystem():
    """Test tool discovery for filesystem server."""
    client = MCPClient()
    tools = client.discover_tools("filesystem")

    assert len(tools) == 3
    tool_names = [tool.name for tool in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_directory" in tool_names

    # Check a specific tool
    read_tool = next(tool for tool in tools if tool.name == "read_file")
    assert read_tool.server_name == "filesystem"
    assert "path" in read_tool.input_schema["properties"]


def test_discover_tools_github():
    """Test tool discovery for GitHub server."""
    client = MCPClient()
    tools = client.discover_tools("github")

    assert len(tools) == 2
    tool_names = [tool.name for tool in tools]
    assert "search_repositories" in tool_names
    assert "get_repository_info" in tool_names


def test_call_tool_filesystem_read_file():
    """Test calling a filesystem read_file tool."""
    client = MCPClient()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content")
        temp_file = f.name

    try:
        result = client.call_tool("read_file", "filesystem", {"path": temp_file})
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["content"] == "Test content"

    finally:
        Path(temp_file).unlink()


def test_call_tool_filesystem_read_nonexistent_file():
    """Test calling read_file tool with nonexistent file."""
    client = MCPClient()

    result = client.call_tool(
        "read_file", "filesystem", {"path": "/nonexistent/file.txt"}
    )
    result_data = json.loads(result)

    assert result_data["success"] is False
    assert "File not found" in result_data["error"]


def test_call_tool_filesystem_write_file():
    """Test calling a filesystem write_file tool."""
    client = MCPClient()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_file = f.name

    try:
        # Remove the file first since we just want the name
        Path(temp_file).unlink()

        result = client.call_tool(
            "write_file",
            "filesystem",
            {"path": temp_file, "content": "New test content"},
        )
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "File written" in result_data["message"]

        # Verify the file was actually written
        with open(temp_file, "r") as f:
            content = f.read()
        assert content == "New test content"

    finally:
        if Path(temp_file).exists():
            Path(temp_file).unlink()


def test_create_langchain_tools():
    """Test creating LangChain tools from MCP tools."""
    client = MCPClient()

    # Add some mock tools
    client.available_tools = [
        MCPTool(
            name="read_file",
            description="Read a file",
            server_name="filesystem",
            input_schema={},
        ),
        MCPTool(
            name="search_repos",
            description="Search repositories",
            server_name="github",
            input_schema={},
        ),
    ]

    langchain_tools = client.create_langchain_tools()

    assert len(langchain_tools) == 2

    tool_names = [tool.name for tool in langchain_tools]
    assert "mcp_filesystem_read_file" in tool_names
    assert "mcp_github_search_repos" in tool_names

    # Check descriptions
    fs_tool = next(tool for tool in langchain_tools if "filesystem" in tool.name)
    assert "[MCP filesystem]" in fs_tool.description
    assert "Read a file" in fs_tool.description


@patch("subprocess.Popen")
def test_start_server(mock_popen):
    """Test starting an MCP server process."""
    mock_process = Mock()
    mock_popen.return_value = mock_process

    client = MCPClient()
    client.server_configs["test_server"] = MCPServerConfig(
        name="test_server",
        command="npx",
        args=["-y", "test-package"],
        env={"TEST_VAR": "value"},
    )

    result = client.start_server("test_server")

    assert result is True
    assert "test_server" in client.server_processes
    assert client.server_processes["test_server"] == mock_process

    # Verify subprocess.Popen was called with correct arguments
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == ["npx", "-y", "test-package"]
    assert kwargs["env"]["TEST_VAR"] == "value"


def test_start_unknown_server():
    """Test starting a server that doesn't exist in config."""
    client = MCPClient()

    result = client.start_server("unknown_server")

    assert result is False
    assert "unknown_server" not in client.server_processes


@patch("subprocess.Popen")
def test_stop_server(mock_popen):
    """Test stopping an MCP server process."""
    mock_process = Mock()
    mock_popen.return_value = mock_process

    client = MCPClient()
    client.server_configs["test_server"] = MCPServerConfig(
        name="test_server", command="npx", args=["-y", "test-package"]
    )

    # Start the server first
    client.start_server("test_server")

    # Now stop it
    client.stop_server("test_server")

    assert "test_server" not in client.server_processes
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once_with(timeout=5)

"""
MCP (Model Context Protocol) Client for GitHub AI Agent

This module provides MCP client functionality to connect to external MCP servers
and integrate their tools with the GitHub AI Agent's existing repository tools.
"""

import asyncio
import json
import logging
import subprocess
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    working_directory: Optional[str] = None


@dataclass
class MCPTool:
    """Represents a tool from an MCP server."""

    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]


class MCPClient:
    """
    MCP Client for connecting to external MCP servers and integrating their tools.

    This client manages connections to MCP servers, discovers available tools,
    and creates LangChain Tool objects that can be used by the ReAct agent.
    """

    def __init__(self, config_file: str = "mcp_config.json"):
        """
        Initialize the MCP client.

        Args:
            config_file: Path to the MCP configuration file
        """
        self.config_file = config_file
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.available_tools: List[MCPTool] = []
        self.server_processes: Dict[str, subprocess.Popen] = {}

    def load_config(self) -> None:
        """Load MCP server configuration from JSON file."""
        config_path = Path(self.config_file)

        if not config_path.exists():
            logger.warning(f"MCP config file not found: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            mcp_servers = config_data.get("mcpServers", {})

            for server_name, server_config in mcp_servers.items():
                self.server_configs[server_name] = MCPServerConfig(
                    name=server_name,
                    command=server_config["command"],
                    args=server_config["args"],
                    env=server_config.get("env"),
                    working_directory=server_config.get("workingDirectory"),
                )

            logger.info(f"Loaded {len(self.server_configs)} MCP server configurations")

        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

    def start_server(self, server_name: str) -> bool:
        """
        Start an MCP server process.

        Args:
            server_name: Name of the server to start

        Returns:
            True if server started successfully, False otherwise
        """
        if server_name not in self.server_configs:
            logger.error(f"Unknown MCP server: {server_name}")
            return False

        if server_name in self.server_processes:
            logger.info(f"MCP server {server_name} already running")
            return True

        config = self.server_configs[server_name]

        try:
            # Prepare environment variables
            env = os.environ.copy()
            if config.env:
                env.update(config.env)

            # Build command list
            command_list = [config.command] + config.args

            # Start the server process
            process = subprocess.Popen(
                command_list,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=config.working_directory,
                text=True,
                shell=True,  # Use shell to resolve commands like npx on Windows
            )

            self.server_processes[server_name] = process
            logger.info(f"Started MCP server: {server_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server {server_name}: {e}")
            return False

    def stop_server(self, server_name: str) -> None:
        """Stop an MCP server process."""
        if server_name in self.server_processes:
            process = self.server_processes[server_name]
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.server_processes[server_name]
            logger.info(f"Stopped MCP server: {server_name}")

    def stop_all_servers(self) -> None:
        """Stop all running MCP server processes."""
        for server_name in list(self.server_processes.keys()):
            self.stop_server(server_name)

    def discover_tools(self, server_name: str) -> List[MCPTool]:
        """
        Discover available tools from an MCP server.

        This is a simplified implementation. In a full MCP implementation,
        you would use the MCP protocol to communicate with servers.

        Args:
            server_name: Name of the server to query

        Returns:
            List of available tools from the server
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Send a "tools/list" request to the MCP server
        # 2. Parse the response to get tool definitions
        # 3. Create MCPTool objects from the definitions

        mock_tools = []

        if server_name == "filesystem":
            mock_tools = [
                MCPTool(
                    name="read_file",
                    description="Read the contents of a file from the filesystem",
                    server_name=server_name,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to read",
                            }
                        },
                        "required": ["path"],
                    },
                ),
                MCPTool(
                    name="write_file",
                    description="Write content to a file on the filesystem",
                    server_name=server_name,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to write",
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file",
                            },
                        },
                        "required": ["path", "content"],
                    },
                ),
                MCPTool(
                    name="list_directory",
                    description="List the contents of a directory",
                    server_name=server_name,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the directory to list",
                            }
                        },
                        "required": ["path"],
                    },
                ),
            ]
        elif server_name == "github":
            mock_tools = [
                MCPTool(
                    name="search_repositories",
                    description="Search for GitHub repositories",
                    server_name=server_name,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for repositories",
                            }
                        },
                        "required": ["query"],
                    },
                ),
                MCPTool(
                    name="get_repository_info",
                    description="Get information about a GitHub repository",
                    server_name=server_name,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Repository owner",
                            },
                            "repo": {
                                "type": "string",
                                "description": "Repository name",
                            },
                        },
                        "required": ["owner", "repo"],
                    },
                ),
            ]

        return mock_tools

    def call_tool(
        self, tool_name: str, server_name: str, parameters: Dict[str, Any]
    ) -> str:
        """
        Call a tool on an MCP server.

        This is a simplified implementation. In a full MCP implementation,
        you would use the MCP protocol to send tool calls.

        Args:
            tool_name: Name of the tool to call
            server_name: Name of the server hosting the tool
            parameters: Parameters to pass to the tool

        Returns:
            JSON string with the tool execution result
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Send a "tools/call" request to the MCP server
        # 2. Include the tool name and parameters
        # 3. Parse the response and return the result

        try:
            # Mock implementation for demonstration
            if server_name == "filesystem":
                if tool_name == "read_file":
                    path = parameters.get("path", "")
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        return json.dumps({"success": True, "content": content})
                    else:
                        return json.dumps({"success": False, "error": "File not found"})
                elif tool_name == "write_file":
                    path = parameters.get("path", "")
                    content = parameters.get("content", "")
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(content)
                        return json.dumps(
                            {"success": True, "message": f"File written: {path}"}
                        )
                    except Exception as e:
                        return json.dumps({"success": False, "error": str(e)})
                elif tool_name == "list_directory":
                    path = parameters.get("path", "")
                    if os.path.exists(path) and os.path.isdir(path):
                        items = os.listdir(path)
                        return json.dumps({"success": True, "items": items})
                    else:
                        return json.dumps(
                            {"success": False, "error": "Directory not found"}
                        )

            elif server_name == "github":
                # Mock GitHub operations
                if tool_name == "search_repositories":
                    query = parameters.get("query", "")
                    return json.dumps(
                        {
                            "success": True,
                            "repositories": [
                                {
                                    "name": f"mock-repo-{query}",
                                    "owner": "mock-owner",
                                    "description": f"Mock repository for query: {query}",
                                }
                            ],
                        }
                    )
                elif tool_name == "get_repository_info":
                    owner = parameters.get("owner", "")
                    repo = parameters.get("repo", "")
                    return json.dumps(
                        {
                            "success": True,
                            "repository": {
                                "name": repo,
                                "owner": owner,
                                "description": f"Mock info for {owner}/{repo}",
                                "stars": 42,
                                "forks": 10,
                            },
                        }
                    )

            return json.dumps({"success": False, "error": "Tool not implemented"})

        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def create_langchain_tools(self) -> List[Tool]:
        """
        Create LangChain Tool objects from available MCP tools.

        Returns:
            List of LangChain Tool objects that can be used by the agent
        """
        langchain_tools = []

        for mcp_tool in self.available_tools:

            def create_tool_func(tool_name: str, server_name: str):
                def tool_func(**kwargs) -> str:
                    return self.call_tool(tool_name, server_name, kwargs)

                return tool_func

            langchain_tool = Tool(
                name=f"mcp_{mcp_tool.server_name}_{mcp_tool.name}",
                description=f"[MCP {mcp_tool.server_name}] {mcp_tool.description}",
                func=create_tool_func(mcp_tool.name, mcp_tool.server_name),
            )

            langchain_tools.append(langchain_tool)

        return langchain_tools

    def initialize(self) -> List[Tool]:
        """
        Initialize the MCP client and return available tools.

        Returns:
            List of LangChain Tool objects from all configured MCP servers
        """
        self.load_config()

        # Start servers and discover tools
        for server_name in self.server_configs:
            if self.start_server(server_name):
                tools = self.discover_tools(server_name)
                self.available_tools.extend(tools)
                logger.info(
                    f"Discovered {len(tools)} tools from MCP server: {server_name}"
                )

        # Create LangChain tools
        langchain_tools = self.create_langchain_tools()
        logger.info(f"Created {len(langchain_tools)} MCP tools for the agent")

        return langchain_tools

    def cleanup(self) -> None:
        """Clean up resources and stop all servers."""
        self.stop_all_servers()

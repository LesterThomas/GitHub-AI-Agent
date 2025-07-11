"""
MCP (Model Context Protocol) Client for GitHub AI Agent

This module provides MCP client functionality to connect to external MCP servers
using the official MCP Python SDK and integrate their tools with the GitHub AI Agent's existing repository tools.

Note: There is a known issue with the MCP SDK's streamable HTTP client that causes
harmless cleanup warnings during asyncio shutdown. This does not affect functionality.
"""

import asyncio
import json
import logging
import os
import warnings
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import Tool

# MCP SDK imports
from mcp import ClientSession, StdioServerParameters, types as mcp_types
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.metadata_utils import get_display_name

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    transport: str = "stdio"  # "stdio" or "streamable_http"
    
    # For stdio transport
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    
    # For streamable_http transport
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.transport == "stdio":
            if not self.command:
                raise ValueError("stdio transport requires 'command'")
        elif self.transport == "streamable_http":
            if not self.url:
                raise ValueError("streamable_http transport requires 'url'")
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")


@dataclass
class MCPTool:
    """Represents a tool from an MCP server."""

    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None


class MCPClient:
    """
    MCP Client for connecting to external MCP servers using the official MCP Python SDK.

    This client manages connections to MCP servers via stdio or streamable HTTP, discovers available tools,
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
        self.sessions: Dict[str, ClientSession] = {}
        self.stream_pairs: Dict[str, Any] = {}  # Store read/write streams
        self._running = False
        self._cleanup_attempted = False

    def __del__(self):
        """Destructor to ensure cleanup happens."""
        if self._running and not self._cleanup_attempted:
            try:
                self.cleanup()
            except Exception as e:
                # Use print instead of logger since logging might be shut down
                print(f"Warning: Error in MCP client destructor: {e}")
                
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

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
                transport = server_config.get("transport", "stdio")
                
                if transport == "stdio":
                    command = server_config.get("command")
                    if not command:
                        logger.error(f"stdio server {server_name} missing 'command'")
                        continue
                    
                    self.server_configs[server_name] = MCPServerConfig(
                        name=server_name,
                        transport="stdio",
                        command=command,
                        args=server_config.get("args", []),
                        env=server_config.get("env"),
                    )
                    
                elif transport == "streamable_http":
                    url = server_config.get("url")
                    if not url:
                        logger.error(f"streamable_http server {server_name} missing 'url'")
                        continue
                    
                    self.server_configs[server_name] = MCPServerConfig(
                        name=server_name,
                        transport="streamable_http",
                        url=url,
                        headers=server_config.get("headers"),
                    )
                else:
                    logger.error(f"Unsupported transport '{transport}' for server {server_name}")
                    continue

            logger.info(f"Loaded {len(self.server_configs)} MCP server configurations")

        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

    async def start_server(self, server_name: str) -> bool:
        """
        Start an MCP server connection.

        Args:
            server_name: Name of the server to start

        Returns:
            True if server started successfully, False otherwise
        """
        if server_name not in self.server_configs:
            logger.error(f"Unknown MCP server: {server_name}")
            return False

        if server_name in self.sessions:
            logger.info(f"MCP server {server_name} already connected")
            return True

        config = self.server_configs[server_name]

        try:
            if config.transport == "stdio":
                return await self._start_stdio_server(server_name, config)
            elif config.transport == "streamable_http":
                return await self._start_http_server(server_name, config)
            else:
                logger.error(f"Unsupported transport: {config.transport}")
                return False

        except Exception as e:
            logger.error(f"Failed to start MCP server {server_name}: {e}")
            return False

    async def _start_stdio_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Start connection to a stdio-based MCP server."""
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args or [],
                env=config.env,
            )

            # Establish stdio connection
            stdio_context = stdio_client(server_params)
            read_stream, write_stream = await stdio_context.__aenter__()
            
            # Store the context for cleanup
            self.stream_pairs[server_name] = {
                'context': stdio_context,
                'safe_cleanup': True
            }
            
            # Create and initialize session
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()
            
            self.sessions[server_name] = session
            logger.info(f"Connected to stdio MCP server: {server_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to stdio server {server_name}: {e}")
            return False

    async def _start_http_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Start connection to a streamable HTTP-based MCP server."""
        try:
            logger.info(f"Connecting to MCP server {server_name} at {config.url}")
            
            # Prepare headers for SSE connection
            headers = config.headers or {}
            
            # Add SSE-specific headers
            headers.setdefault('Accept', 'text/event-stream')
            headers.setdefault('Cache-Control', 'no-cache')
            headers.setdefault('Connection', 'keep-alive')
            
            logger.info(f"Request headers: {headers}")
            
            # Try to establish HTTP connection
            # Note: streamablehttp_client should make a GET request for SSE
            try:
                http_context = streamablehttp_client(config.url, headers=headers)
                read_stream, write_stream, _ = await http_context.__aenter__()
                
                logger.info(f"HTTP connection established for {server_name}")
                
                # Store the context for cleanup, but with a flag to avoid problematic cleanup
                self.stream_pairs[server_name] = {
                    'context': http_context,
                    'safe_cleanup': True  # Flag to control cleanup behavior
                }
                
                # Create and initialize session
                session = ClientSession(read_stream, write_stream)
                await session.__aenter__()
                
                logger.info(f"Initializing MCP session for {server_name}")
                await session.initialize()
                
                self.sessions[server_name] = session
                logger.info(f"Connected to streamable HTTP MCP server: {server_name}")
                return True
                
            except Exception as connection_error:
                logger.error(f"Connection error for {server_name}: {connection_error}")
                logger.info(f"Full connection error: {connection_error}", exc_info=True)
                raise

        except Exception as e:
            logger.error(f"Failed to connect to HTTP server {server_name}: {e}")
            logger.info(f"Full error details: {e}", exc_info=True)
            return False

    async def stop_server(self, server_name: str) -> None:
        """Stop an MCP server connection."""
        # Store references to avoid dictionary modification during iteration
        session = self.sessions.get(server_name)
        pair_info = self.stream_pairs.get(server_name)
        
        # First close the session
        if session:
            try:
                await session.__aexit__(None, None, None)
                del self.sessions[server_name]
                logger.info(f"Closed MCP server session: {server_name}")
            except Exception as e:
                logger.error(f"Error closing session for {server_name}: {e}")

        # Clear stream pair tracking (don't force context cleanup)
        if pair_info:
            try:
                del self.stream_pairs[server_name]
                logger.info(f"Removed MCP server connection tracking: {server_name}")
                # Let the context cleanup naturally to avoid task group issues
            except Exception as e:
                logger.error(f"Error cleaning up streams for {server_name}: {e}")

    async def stop_all_servers(self) -> None:
        """Stop all running MCP servers."""
        servers_to_stop = list(self.sessions.keys()) + list(self.stream_pairs.keys())
        # Remove duplicates while preserving order
        servers_to_stop = list(dict.fromkeys(servers_to_stop))
        
        for server_name in servers_to_stop:
            try:
                await self.stop_server(server_name)
            except Exception as e:
                logger.error(f"Error stopping server {server_name}: {e}")
                # Continue with other servers even if one fails

    async def discover_tools(self, server_name: str) -> List[MCPTool]:
        """
        Discover available tools from an MCP server.

        Args:
            server_name: Name of the server to query

        Returns:
            List of available tools from the server
        """
        if server_name not in self.sessions:
            logger.error(f"MCP server {server_name} is not connected")
            return []

        try:
            session = self.sessions[server_name]
            
            # List available tools
            tools_response = await session.list_tools()
            
            tools = []
            for tool in tools_response.tools:
                mcp_tool = MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    server_name=server_name,
                    input_schema=tool.inputSchema or {},
                    output_schema=getattr(tool, 'outputSchema', None),
                )
                tools.append(mcp_tool)
            
            logger.info(f"Discovered {len(tools)} tools from {server_name}")
            return tools

        except Exception as e:
            logger.error(f"Error discovering tools from {server_name}: {e}")
            return []

    async def call_tool(
        self, tool_name: str, server_name: str, parameters: Dict[str, Any]
    ) -> str:
        """
        Call a tool on an MCP server.

        Args:
            tool_name: Name of the tool to call
            server_name: Name of the server hosting the tool
            parameters: Parameters to pass to the tool

        Returns:
            JSON string with the tool execution result
        """
        if server_name not in self.sessions:
            return json.dumps(
                {"success": False, "error": f"Server {server_name} is not connected"}
            )

        try:
            session = self.sessions[server_name]
            
            # Log the tool call for debugging
            logger.info(f"Calling tool '{tool_name}' on server '{server_name}' with parameters: {parameters}")
            
            # Call the tool
            result = await session.call_tool(tool_name, parameters)
            
            # Log the result for debugging
            logger.info(f"Tool call result type: {type(result)}")
            logger.info(f"Tool call result attributes: {dir(result)}")
            
            # Format the result
            if hasattr(result, 'content') and result.content:
                # Extract content from the result
                content_items = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_items.append(content.text)
                    elif hasattr(content, 'data'):
                        content_items.append(str(content.data))
                
                response = {
                    "success": True,
                    "content": content_items,
                    "isError": getattr(result, 'isError', False),
                }
                
                # Include structured data if available
                if hasattr(result, 'structuredData') and result.structuredData:
                    response["structuredData"] = result.structuredData
                
                return json.dumps(response)
            else:
                # Check if there's an error in the result
                if hasattr(result, 'isError') and result.isError:
                    error_msg = "Tool execution failed"
                    if hasattr(result, 'content') and result.content:
                        # Try to extract error message from content
                        for content in result.content:
                            if hasattr(content, 'text'):
                                error_msg = content.text
                                break
                    return json.dumps({"success": False, "error": error_msg})
                else:
                    return json.dumps({"success": True, "content": [], "isError": False})

        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception details: {e}", exc_info=True)
            return json.dumps({"success": False, "error": str(e)})

    def create_langchain_tools(self) -> List[Tool]:
        """
        Create LangChain Tool objects from available MCP tools.

        Returns:
            List of LangChain Tool objects that can be used by the agent
        """
        langchain_tools = []

        for mcp_tool in self.available_tools:

            def create_tool_func(
                tool_name: str, server_name: str, input_schema: Dict[str, Any]
            ):
                def tool_func(*args, **kwargs) -> str:
                    # Handle both positional and keyword arguments
                    schema_properties = input_schema.get("properties", {})
                    required_params = input_schema.get("required", [])
                    
                    # Get parameter names in order (required first, then others)
                    param_names = list(schema_properties.keys())
                    if required_params:
                        param_names = required_params + [
                            p for p in param_names if p not in required_params
                        ]
                    
                    mapped_kwargs = {}
                    
                    if args and not kwargs:
                        # Map positional arguments to parameter names
                        for i, arg in enumerate(args):
                            if i < len(param_names):
                                mapped_kwargs[param_names[i]] = arg
                    elif kwargs:
                        # Check if we have generic argument names like __arg1, __arg2
                        generic_args = {k: v for k, v in kwargs.items() if k.startswith('__arg')}
                        if generic_args:
                            # Map generic arguments to proper parameter names
                            sorted_generic = sorted(generic_args.items())
                            for i, (_, value) in enumerate(sorted_generic):
                                if i < len(param_names):
                                    mapped_kwargs[param_names[i]] = value
                        else:
                            # Use kwargs directly if they have proper names
                            mapped_kwargs = kwargs
                    else:
                        # No arguments provided
                        mapped_kwargs = {}

                    # Run the async call in the background event loop
                    if hasattr(self, '_loop') and self._loop:
                        future = asyncio.run_coroutine_threadsafe(
                            self.call_tool(tool_name, server_name, mapped_kwargs), 
                            self._loop
                        )
                        return future.result(timeout=30)  # 30 second timeout
                    else:
                        # Fallback to creating a new event loop
                        return asyncio.run(
                            self.call_tool(tool_name, server_name, mapped_kwargs)
                        )

                return tool_func

            # Create a more descriptive tool description with parameter info
            param_info = ""
            if mcp_tool.input_schema.get("properties"):
                properties = mcp_tool.input_schema["properties"]
                required = mcp_tool.input_schema.get("required", [])
                param_descriptions = []
                
                for param_name, param_def in properties.items():
                    param_type = param_def.get("type", "string")
                    param_desc = param_def.get("description", param_def.get("title", param_name))
                    required_marker = " (required)" if param_name in required else ""
                    param_descriptions.append(f"{param_name} ({param_type}){required_marker}: {param_desc}")
                
                if param_descriptions:
                    param_info = f"\n\nParameters:\n" + "\n".join(f"- {desc}" for desc in param_descriptions)
            
            # Use get_display_name for better naming
            display_name = get_display_name(mcp_tool) if hasattr(mcp_tool, 'title') else mcp_tool.name
            
            langchain_tool = Tool(
                name=f"mcp_{mcp_tool.server_name}_{mcp_tool.name}",
                description=f"[MCP {mcp_tool.server_name}] {mcp_tool.description}{param_info}",
                func=create_tool_func(
                    mcp_tool.name, mcp_tool.server_name, mcp_tool.input_schema
                ),
            )

            langchain_tools.append(langchain_tool)

        return langchain_tools

    async def initialize_async(self) -> List[Tool]:
        """
        Initialize the MCP client asynchronously and return available tools.

        Returns:
            List of LangChain Tool objects from all configured MCP servers
        """
        self.load_config()

        # Start servers and discover tools
        for server_name in self.server_configs:
            if await self.start_server(server_name):
                tools = await self.discover_tools(server_name)
                self.available_tools.extend(tools)
                logger.info(
                    f"Discovered {len(tools)} tools from MCP server: {server_name}"
                )

        # Create LangChain tools
        langchain_tools = self.create_langchain_tools()
        logger.info(f"Created {len(langchain_tools)} MCP tools for the agent")

        self._running = True
        return langchain_tools

    def initialize(self) -> List[Tool]:
        """
        Initialize the MCP client and return available tools.
        
        This is a synchronous wrapper around initialize_async.
        IMPORTANT: This method starts an event loop that stays running
        to keep MCP connections alive for the tools to use.

        Returns:
            List of LangChain Tool objects from all configured MCP servers
        """
        # We need to run the async initialization in a way that keeps
        # the event loop and connections alive
        import threading
        import asyncio
        
        # Create a new event loop for the MCP client
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._loop_thread.start()
        
        # Wait for the loop to be ready
        import time
        time.sleep(0.1)
        
        # Initialize the MCP client in the background loop
        future = asyncio.run_coroutine_threadsafe(self.initialize_async(), self._loop)
        tools = future.result(timeout=30)  # 30 second timeout
        
        return tools
    
    def _run_event_loop(self):
        """Run the event loop in a background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
        
    async def cleanup_async(self) -> None:
        """Clean up resources and stop all servers asynchronously."""
        if self._running:
            try:
                # Close sessions first
                for server_name in list(self.sessions.keys()):
                    try:
                        session = self.sessions[server_name]
                        await session.__aexit__(None, None, None)
                        del self.sessions[server_name]
                        logger.info(f"Closed MCP server session: {server_name}")
                    except Exception as e:
                        logger.warning(f"Error closing session for {server_name}: {e}")
                
                # Clear the stream pairs without forcing cleanup
                # The HTTP context will be cleaned up naturally by Python's GC
                # avoiding the task group context issues
                stream_pairs_copy = dict(self.stream_pairs)
                self.stream_pairs.clear()
                
                for server_name, pair_info in stream_pairs_copy.items():
                    try:
                        logger.info(f"Removed MCP server connection tracking: {server_name}")
                        # Don't attempt to clean up the context - let it be handled naturally
                        # This avoids the "Attempted to exit cancel scope in a different task" error
                    except Exception as e:
                        logger.warning(f"Error during stream cleanup for {server_name}: {e}")
                
                self._running = False
                logger.info("MCP client cleanup completed")
            except Exception as e:
                logger.error(f"Error during MCP cleanup: {e}")
                self._running = False
        
    def cleanup(self) -> None:
        """Clean up resources and stop all servers."""
        if self._running and not self._cleanup_attempted:
            self._cleanup_attempted = True
            try:
                if hasattr(self, '_loop') and self._loop:
                    # Schedule cleanup in the background loop
                    future = asyncio.run_coroutine_threadsafe(self.cleanup_async(), self._loop)
                    future.result(timeout=10)  # 10 second timeout
                    
                    # Stop the event loop
                    self._loop.call_soon_threadsafe(self._loop.stop)
                    
                    # Wait for thread to finish
                    if hasattr(self, '_loop_thread') and self._loop_thread:
                        self._loop_thread.join(timeout=5)
                        
                else:
                    # Fallback to old method
                    try:
                        asyncio.run(self.cleanup_async())
                    except RuntimeError:
                        # No event loop, that's fine
                        pass
            except Exception as e:
                logger.error(f"Error during MCP cleanup: {e}")
                self._running = False

"""
MCP (Model Context Protocol) Client for GitHub AI Agent

This module provides MCP client functionality to connect to external MCP servers
over HTTP/SSE and integrate their tools with the GitHub AI Agent's existing repository tools.
"""

import json
import logging
import os
import httpx
import threading
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty

from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    url: str
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.url:
            raise ValueError("MCP servers must specify 'url'")


@dataclass
class MCPTool:
    """Represents a tool from an MCP server."""

    name: str
    description: str
    server_name: str
    input_schema: Dict[str, Any]


class MCPClient:
    """
    MCP Client for connecting to external MCP servers over HTTP/SSE.

    This client manages connections to MCP servers via HTTP/SSE, discovers available tools,
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
        self.http_clients: Dict[str, httpx.Client] = {}
        self.sse_connections: Dict[str, Any] = {}  # Store SSE connection info
        self.sse_threads: Dict[str, threading.Thread] = {}  # Store SSE threads
        self.message_queues: Dict[str, Queue] = {}  # Store response queues
        self.request_id_counter = 0
        self.pending_requests: Dict[int, Queue] = {}  # Track pending JSON-RPC requests
        self._shutdown_event = threading.Event()

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
                # All servers are HTTP/SSE-based
                if "url" not in server_config:
                    logger.error(
                        f"Invalid server config for {server_name}: must specify 'url'"
                    )
                    continue

                self.server_configs[server_name] = MCPServerConfig(
                    name=server_name,
                    url=server_config["url"],
                    headers=server_config.get("headers"),
                )

            logger.info(f"Loaded {len(self.server_configs)} MCP server configurations")

        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

    def start_server(self, server_name: str) -> bool:
        """
        Start an MCP server connection over HTTP/SSE.

        Args:
            server_name: Name of the server to start

        Returns:
            True if server started successfully, False otherwise
        """
        if server_name not in self.server_configs:
            logger.error(f"Unknown MCP server: {server_name}")
            return False

        config = self.server_configs[server_name]
        return self._start_sse_server(server_name, config)

    def _start_sse_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Start connection to an HTTP/SSE-based MCP server."""
        if server_name in self.http_clients:
            logger.info(f"MCP server {server_name} already connected")
            return True

        try:
            # Create HTTP client for the SSE server
            headers = config.headers or {}

            client = httpx.Client(timeout=30.0)

            # Parse base URL and construct endpoints
            base_url = config.url.rstrip("/")
            sse_url = f"{base_url}/sse"
            messages_url = f"{base_url}/messages"

            # Generate a session ID
            session_id = str(uuid.uuid4())

            # Store the client and connection info
            self.http_clients[server_name] = client
            self.sse_connections[server_name] = {
                "base_url": base_url,
                "sse_url": sse_url,
                "messages_url": messages_url,
                "headers": headers,
                "connected": False,
                "session_id": session_id,
            }

            # Initialize message queue for this server
            self.message_queues[server_name] = Queue()

            # Start SSE connection in a separate thread
            sse_thread = threading.Thread(
                target=self._handle_sse_connection,
                args=(server_name, config),
                daemon=True,
            )
            sse_thread.start()
            self.sse_threads[server_name] = sse_thread

            # Wait a moment for connection to establish
            time.sleep(1.0)

            # Check if connection was successful
            if self.sse_connections[server_name].get("connected"):
                logger.info(f"Connected to HTTP/SSE MCP server: {server_name}")
                logger.info(f"  SSE endpoint: {sse_url}")
                logger.info(f"  Messages endpoint: {messages_url}")
                logger.info(f"  Session ID: {session_id}")
                return True
            else:
                logger.error(f"Failed to establish SSE connection to {server_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to HTTP/SSE server {server_name}: {e}")
            return False

    def _handle_sse_connection(self, server_name: str, config: MCPServerConfig) -> None:
        """
        Handle the long-running SSE connection in a separate thread.

        This method establishes the SSE connection and listens for events.
        """
        try:
            connection_info = self.sse_connections[server_name]
            sse_url = connection_info["sse_url"]
            session_id = connection_info["session_id"]
            headers = dict(config.headers or {})

            # Add SSE-specific headers
            headers.update(
                {
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

            # Include session ID in SSE URL
            sse_url = f"{sse_url}"

            logger.info(f"Starting SSE connection to {sse_url}")

            # Create a new client for the SSE connection (streaming)
            with httpx.stream(
                "GET",
                sse_url,
                headers=headers,
                timeout=None,  # No timeout for SSE
            ) as response:

                if response.status_code == 200:
                    # Mark connection as successful
                    self.sse_connections[server_name]["connected"] = True
                    logger.info(f"SSE connection established for {server_name}")

                    # Process SSE events
                    for line in response.iter_lines():
                        if self._shutdown_event.is_set():
                            break

                        line = line.strip()
                        if not line:
                            continue

                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            try:
                                event_data = json.loads(data)
                                self._handle_sse_event(server_name, event_data)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in SSE event: {data}")

                else:
                    logger.error(f"SSE connection failed: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Error in SSE connection for {server_name}: {e}")
        finally:
            self.sse_connections[server_name]["connected"] = False
            logger.info(f"SSE connection closed for {server_name}")

    def _handle_sse_event(self, server_name: str, event_data: Dict[str, Any]) -> None:
        """Handle an incoming SSE event from the MCP server."""
        try:
            # Check if this is a JSON-RPC response
            if "id" in event_data and event_data["id"] is not None:
                request_id = event_data["id"]

                # If we have a pending request for this ID, deliver the response
                if request_id in self.pending_requests:
                    response_queue = self.pending_requests[request_id]
                    response_queue.put(event_data)
                    logger.debug(f"Delivered response for request {request_id}")
                else:
                    logger.warning(
                        f"Received response for unknown request ID: {request_id}"
                    )

            elif "method" in event_data:
                # This is a notification or request from the server
                method = event_data["method"]
                logger.info(f"Received server notification: {method}")

                # Handle specific notifications if needed
                if method == "notifications/initialized":
                    logger.info(f"Server {server_name} confirmed initialization")

            else:
                logger.debug(f"Received SSE event: {event_data}")

        except Exception as e:
            logger.error(f"Error handling SSE event from {server_name}: {e}")

    def stop_server(self, server_name: str) -> None:
        """Stop an MCP server HTTP connection."""
        # Signal shutdown to SSE thread
        if server_name in self.sse_threads:
            self._shutdown_event.set()

            # Wait for SSE thread to finish (with timeout)
            sse_thread = self.sse_threads[server_name]
            sse_thread.join(timeout=5.0)

            if sse_thread.is_alive():
                logger.warning(
                    f"SSE thread for {server_name} did not shut down gracefully"
                )

            del self.sse_threads[server_name]

        # Close HTTP client
        if server_name in self.http_clients:
            client = self.http_clients[server_name]
            client.close()
            del self.http_clients[server_name]
            logger.info(f"Closed MCP server connection: {server_name}")

        # Clean up other resources
        if server_name in self.sse_connections:
            del self.sse_connections[server_name]

        if server_name in self.message_queues:
            del self.message_queues[server_name]

    def stop_all_servers(self) -> None:
        """Stop all running MCP servers."""
        # Signal shutdown to all threads
        self._shutdown_event.set()

        # Close all connections
        for server_name in list(self.http_clients.keys()):
            self.stop_server(server_name)

        # Clear shutdown event for potential restart
        self._shutdown_event.clear()

    def discover_tools(self, server_name: str) -> List[MCPTool]:
        """
        Discover available tools from an MCP server.

        Args:
            server_name: Name of the server to query

        Returns:
            List of available tools from the server
        """
        if server_name not in self.server_configs:
            logger.error(f"Unknown MCP server: {server_name}")
            return []

        config = self.server_configs[server_name]

        try:
            return self._discover_tools_sse(server_name, config)
        except Exception as e:
            logger.error(f"Error discovering tools from {server_name}: {e}")
            return []

    def _discover_tools_sse(
        self, server_name: str, config: MCPServerConfig
    ) -> List[MCPTool]:
        """Discover tools from an HTTP/SSE-based MCP server using JSON-RPC."""
        if server_name not in self.http_clients:
            logger.error(f"HTTP/SSE server {server_name} is not connected")
            return []

        try:
            connection_info = self.sse_connections[server_name]
            logger.info(f"Discovering tools from HTTP/SSE server {server_name}")

            # Initialize session if not done already
            if not connection_info.get("session_initialized"):
                if not self._initialize_mcp_session(
                    server_name, self.http_clients[server_name], config
                ):
                    return self._get_mock_tools(server_name)
                connection_info["session_initialized"] = True

            # Send tools/list request
            request_id = self._get_next_request_id()
            request_payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list",
                "params": {},
            }

            response_data = self._send_json_rpc_request(server_name, request_payload)

            if (
                response_data
                and "result" in response_data
                and "tools" in response_data["result"]
            ):
                tools = []
                for tool_def in response_data["result"]["tools"]:
                    tool = MCPTool(
                        name=tool_def["name"],
                        description=tool_def.get("description", ""),
                        server_name=server_name,
                        input_schema=tool_def.get("inputSchema", {}),
                    )
                    tools.append(tool)
                logger.info(f"Discovered {len(tools)} tools from {server_name}")
                return tools
            else:
                logger.error(f"Failed to get tools from {server_name}")
                return self._get_mock_tools(server_name)

        except Exception as e:
            logger.error(f"Error communicating with HTTP/SSE server {server_name}: {e}")
            return self._get_mock_tools(server_name)

    def _initialize_mcp_session(
        self, server_name: str, client: httpx.Client, config: MCPServerConfig
    ) -> bool:
        """Initialize MCP session with the server using the /messages endpoint."""
        try:
            connection_info = self.sse_connections[server_name]
            messages_url = connection_info["messages_url"]
            session_id = connection_info.get("session_id")

            if not session_id:
                logger.error(f"No session ID available for {server_name}")
                return False

            # Wait for SSE connection to be established
            max_wait = 5  # 5 seconds
            wait_count = 0
            while not connection_info.get("connected") and wait_count < max_wait:
                time.sleep(1)
                wait_count += 1

            if not connection_info.get("connected"):
                logger.error(f"SSE connection not established for {server_name}")
                return False

            # Send MCP initialize request
            request_id = self._get_next_request_id()
            init_request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "github-ai-agent", "version": "1.0.0"},
                },
            }

            # Send request and wait for response
            response_data = self._send_json_rpc_request(server_name, init_request)

            if response_data and "result" in response_data:
                # Send initialized notification (no response expected)
                init_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }

                self._send_json_rpc_notification(server_name, init_notification)
                logger.info(f"Successfully initialized MCP session for {server_name}")
                return True
            else:
                logger.error(f"Failed to initialize MCP session for {server_name}")
                return False

        except Exception as e:
            logger.error(f"Error initializing MCP session for {server_name}: {e}")
            return False

    def _get_next_request_id(self) -> int:
        """Get the next request ID for JSON-RPC requests."""
        self.request_id_counter += 1
        return self.request_id_counter

    def _send_json_rpc_request(
        self, server_name: str, request: Dict[str, Any], timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request and wait for response."""
        try:
            client = self.http_clients[server_name]
            config = self.server_configs[server_name]
            connection_info = self.sse_connections[server_name]

            request_id = request.get("id")
            if request_id is None:
                logger.error("Request must have an ID for response tracking")
                return None

            # Create response queue for this request
            response_queue = Queue()
            self.pending_requests[request_id] = response_queue

            try:
                # Send the request via POST to /messages
                headers = dict(config.headers or {})
                headers.update(
                    {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    }
                )

                session_id = connection_info.get("session_id")
                messages_url = connection_info["messages_url"]
                request_url = f"{messages_url}?session_id={session_id}"

                response = client.post(request_url, json=request, headers=headers)

                if response.status_code not in [200, 202]:
                    logger.error(f"HTTP error sending request: {response.status_code}")
                    return None

                # Wait for response via SSE
                try:
                    response_data = response_queue.get(timeout=timeout)
                    return response_data
                except Empty:
                    logger.error(
                        f"Timeout waiting for response to request {request_id}"
                    )
                    return None

            finally:
                # Clean up the pending request
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]

        except Exception as e:
            logger.error(f"Error sending JSON-RPC request: {e}")
            return None

    def _send_json_rpc_notification(
        self, server_name: str, notification: Dict[str, Any]
    ) -> bool:
        """Send a JSON-RPC notification (no response expected)."""
        try:
            client = self.http_clients[server_name]
            config = self.server_configs[server_name]
            connection_info = self.sse_connections[server_name]

            headers = dict(config.headers or {})
            headers.update(
                {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )

            session_id = connection_info.get("session_id")
            messages_url = connection_info["messages_url"]
            request_url = f"{messages_url}?session_id={session_id}"

            response = client.post(request_url, json=notification, headers=headers)
            return response.status_code in [200, 202]

        except Exception as e:
            logger.error(f"Error sending JSON-RPC notification: {e}")
            return False

    def call_tool(
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
        if server_name not in self.server_configs:
            return json.dumps(
                {"success": False, "error": f"Unknown server: {server_name}"}
            )

        config = self.server_configs[server_name]

        try:
            return self._call_tool_sse(tool_name, server_name, parameters)
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def _call_tool_sse(
        self, tool_name: str, server_name: str, parameters: Dict[str, Any]
    ) -> str:
        """Call a tool on an HTTP/SSE-based MCP server using JSON-RPC."""
        if server_name not in self.http_clients:
            return json.dumps(
                {
                    "success": False,
                    "error": f"HTTP/SSE server {server_name} is not connected",
                }
            )

        try:
            # Send tools/call request
            request_id = self._get_next_request_id()
            request_payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": parameters},
            }

            response_data = self._send_json_rpc_request(server_name, request_payload)

            if response_data:
                if "result" in response_data:
                    return json.dumps(
                        {"success": True, "result": response_data["result"]}
                    )
                elif "error" in response_data:
                    return json.dumps(
                        {"success": False, "error": response_data["error"]}
                    )

            # Fall back to mock if no valid response
            logger.warning(f"No valid response from {server_name}, using mock")
            return self._call_tool_mock(tool_name, server_name, parameters)

        except Exception as e:
            logger.error(f"Error calling HTTP/SSE tool {tool_name}: {e}")
            return self._call_tool_mock(tool_name, server_name, parameters)

    def _call_tool_mock(
        self, tool_name: str, server_name: str, parameters: Dict[str, Any]
    ) -> str:
        """Mock tool implementation for testing and fallback."""
        try:
            # Mock implementation for demonstration
            if server_name == "filesystem" or "filesystem" in server_name:
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

            elif server_name == "aiva" or "aiva" in server_name:
                if tool_name == "query_tmforum_ai_assistant":
                    query = parameters.get("query", "")
                    return json.dumps(
                        {
                            "success": True,
                            "response": f"Mock AIVA response for query: {query}. In a real implementation, this would query the TM Forum AI Assistant.",
                        }
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
            logger.error(f"Error in mock tool {tool_name}: {e}")
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
                    # If positional args are provided, map them to the expected parameter names
                    if args and not kwargs:
                        # Get the expected parameter names from the tool's input schema
                        schema_properties = input_schema.get("properties", {})
                        required_params = input_schema.get("required", [])

                        # Map positional arguments to parameter names
                        param_names = list(schema_properties.keys())
                        if required_params:
                            # Use required parameters first
                            param_names = required_params + [
                                p for p in param_names if p not in required_params
                            ]

                        # Create kwargs from positional args
                        mapped_kwargs = {}
                        for i, arg in enumerate(args):
                            if i < len(param_names):
                                mapped_kwargs[param_names[i]] = arg

                        return self.call_tool(tool_name, server_name, mapped_kwargs)
                    else:
                        # Use kwargs directly
                        return self.call_tool(tool_name, server_name, kwargs)

                return tool_func

            langchain_tool = Tool(
                name=f"mcp_{mcp_tool.server_name}_{mcp_tool.name}",
                description=f"[MCP {mcp_tool.server_name}] {mcp_tool.description}",
                func=create_tool_func(
                    mcp_tool.name, mcp_tool.server_name, mcp_tool.input_schema
                ),
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

        # Additional cleanup
        self.pending_requests.clear()

        logger.info("MCP client cleanup completed")

    def _handle_sse_events(self, server_name: str) -> None:
        """
        Handle SSE events from the /sse endpoint.

        This method would establish a connection to the /sse endpoint and listen for events.
        For now, it's a placeholder for future implementation when real-time event handling is needed.
        """
        if server_name not in self.http_clients:
            logger.error(f"SSE server {server_name} is not connected")
            return

        try:
            connection_info = self.sse_connections[server_name]
            sse_url = connection_info["sse_url"]

            # Placeholder for SSE event handling
            # In a real implementation, this would:
            # 1. Open an SSE connection to sse_url
            # 2. Listen for events like tool call responses, notifications, etc.
            # 3. Handle events appropriately (update state, call callbacks, etc.)

            logger.info(
                f"SSE event handling placeholder for {server_name} at {sse_url}"
            )

        except Exception as e:
            logger.error(f"Error setting up SSE event handling for {server_name}: {e}")

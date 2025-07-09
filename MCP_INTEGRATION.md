# MCP (Model Context Protocol) Integration Guide

## Overview

The GitHub AI Agent supports integration with external MCP (Model Context Protocol) servers to extend its capabilities beyond the built-in repository management tools. This integration allows the agent to access additional tools for filesystem operations, enhanced GitHub functionality, and other specialized services.

## Architecture

### MCP Client Components

- **MCPClient**: Main client class that manages MCP server connections
- **MCPServerConfig**: Configuration data class for server definitions
- **MCPTool**: Represents individual tools from MCP servers
- **Tool Integration**: Seamless integration with LangChain's Tool framework

### Integration Flow

1. **Configuration Loading**: MCP client reads `mcp_config.json` on startup
2. **Server Startup**: Configured servers are started as subprocess processes
3. **Tool Discovery**: Available tools are discovered from each server
4. **LangChain Integration**: MCP tools are converted to LangChain Tool objects
5. **Agent Integration**: Tools are added to the ReAct agent alongside repository tools

## Configuration

### Basic Configuration

Create an `mcp_config.json` file in the project root:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\username\\Documents"
      ]
    }
  }
}
```

### Advanced Configuration

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/user/workspace"
      ],
      "env": {
        "NODE_ENV": "production"
      },
      "workingDirectory": "/app"
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    },
    "obsidian": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@smithery/cli@latest",
        "run",
        "mcp-obsidian",
        "--config",
        "{\"vaultPath\":\"C:\\\\Users\\\\username\\\\Documents\\\\ObsidianVault\"}"
      ]
    }
  }
}
```

## Available MCP Servers

### 1. Filesystem Server (`@modelcontextprotocol/server-filesystem`)

**Purpose**: Local filesystem operations

**Tools**:
- `read_file`: Read file contents
- `write_file`: Write content to files
- `list_directory`: List directory contents
- `create_directory`: Create directories
- `delete_file`: Delete files

**Configuration**:
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"]
  }
}
```

### 2. GitHub Server (`@modelcontextprotocol/server-github`)

**Purpose**: Enhanced GitHub operations

**Tools**:
- `search_repositories`: Search GitHub repositories
- `get_repository_info`: Get repository metadata
- `list_issues`: List repository issues
- `create_issue`: Create new issues

**Configuration**:
```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token_here"
    }
  }
}
```

### 3. Obsidian Server (`@smithery/cli mcp-obsidian`)

**Purpose**: Obsidian vault management

**Tools**:
- `read_note`: Read note contents
- `write_note`: Create/update notes
- `search_notes`: Search within vault
- `list_notes`: List all notes

**Configuration**:
```json
{
  "obsidian": {
    "command": "cmd",
    "args": [
      "/c", "npx", "-y", "@smithery/cli@latest", "run", "mcp-obsidian",
      "--config", "{\"vaultPath\":\"C:\\\\path\\\\to\\\\vault\"}"
    ]
  }
}
```

## Tool Usage in Agent

### Tool Naming Convention

MCP tools are prefixed with `mcp_{server_name}_{tool_name}`:
- `mcp_filesystem_read_file`
- `mcp_github_search_repositories`
- `mcp_obsidian_read_note`

### Example Agent Interaction

When processing an issue, the agent can now use MCP tools:

```
Issue: "Create a summary of the project structure and save it to my local documents"

Agent reasoning:
1. Use `list_files_in_repo` to explore the repository
2. Use `mcp_filesystem_list_directory` to check local documents folder
3. Use `create_file_in_repo` to create summary in repository
4. Use `mcp_filesystem_write_file` to save copy locally
```

### Tool Descriptions

Each MCP tool includes a descriptive prefix in its description:
- `[MCP filesystem] Read the contents of a file from the filesystem`
- `[MCP github] Search for GitHub repositories`

## Error Handling

### Server Startup Errors

If an MCP server fails to start:
1. Error is logged with details
2. Agent continues with remaining tools
3. MCP functionality is gracefully disabled

### Tool Execution Errors

Tool execution errors are handled gracefully:
1. JSON error responses are returned
2. Errors are logged for debugging
3. Agent can continue with other tools

### Network/Connection Issues

Connection problems are handled with:
1. Timeout handling for server communication
2. Automatic retry mechanisms
3. Fallback to repository-only tools

## Development

### Adding New MCP Servers

1. **Install the MCP server**: Use npm, pip, or other package manager
2. **Update configuration**: Add server configuration to `mcp_config.json`
3. **Test connectivity**: Verify server starts and responds
4. **Update documentation**: Document new tools and capabilities

### Custom MCP Servers

You can create custom MCP servers that follow the MCP protocol:

1. **Implement MCP Protocol**: Follow MCP specification for message handling
2. **Define Tools**: Specify tool schemas and implementations
3. **Handle Requests**: Process tool calls and return structured responses
4. **Configure Agent**: Add server configuration to `mcp_config.json`

### Testing MCP Integration

```bash
# Run MCP-specific tests
uv run pytest tests/test_mcp_client.py

# Run integration tests
uv run pytest tests/test_mcp_integration.py

# Run all tests including MCP
uv run pytest
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Server won't start | Missing dependencies | Install MCP server packages |
| Permission denied | Insufficient file permissions | Check directory access rights |
| Tool not found | Server not responding | Verify server configuration |
| JSON parse errors | Malformed responses | Check server implementation |

### Debug Mode

Enable debug logging to see MCP operations:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Run with enhanced logging
uv run python main.py
```

### Log Output

MCP operations are logged with specific prefixes:
- `🔧 MCP_INIT`: MCP client initialization
- `🔧 MCP_TOOLS`: Tool discovery and loading
- `🔧 MCP_CLEANUP`: Server shutdown and cleanup
- `❌ MCP_ERROR`: MCP-related errors

## Security Considerations

### Environment Variables

- Store sensitive tokens in environment variables
- Use `.env` files for local development
- Never commit tokens to version control

### File System Access

- Limit filesystem server access to specific directories
- Use absolute paths in configuration
- Consider sandboxing for production environments

### Network Access

- Configure firewalls for MCP server communication
- Use secure authentication methods
- Monitor server resource usage

## Performance Considerations

### Server Startup Time

- MCP servers add startup time to agent initialization
- Consider caching strategies for frequently used tools
- Monitor server memory usage

### Tool Execution Speed

- Some MCP tools may be slower than built-in tools
- Implement timeouts for long-running operations
- Consider async execution for independent operations

### Resource Management

- MCP servers consume additional system resources
- Implement proper cleanup on agent shutdown
- Monitor process counts and memory usage

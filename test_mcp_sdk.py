#!/usr/bin/env python3
"""
Test script to verify MCP client integration with the official MCP SDK.
"""

import asyncio
import json
import logging
from pathlib import Path
from github_ai_agent.mcp_client import MCPClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_client():
    """Test the MCP client with the official SDK."""
    
    # Create test config
    test_config = {
        "mcpServers": {
            "filesystem": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp.server.filesystem", "--path", "."]
            }
        }
    }
    
    # Write test config
    config_path = Path("test_mcp_config.json")
    with open(config_path, "w") as f:
        json.dump(test_config, f, indent=2)
    
    try:
        # Initialize MCP client
        client = MCPClient(config_file="test_mcp_config.json")
        
        # Test async initialization
        tools = await client.initialize_async()
        
        logger.info(f"Successfully initialized MCP client with {len(tools)} tools")
        
        # List discovered tools
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        
        # Test cleanup
        await client.cleanup_async()
        logger.info("Successfully cleaned up MCP client")
        
    except Exception as e:
        logger.error(f"Error testing MCP client: {e}")
        logger.exception("Full traceback:")
    
    finally:
        # Clean up test config
        if config_path.exists():
            config_path.unlink()

def test_sync_client():
    """Test the synchronous interface."""
    
    # Create test config
    test_config = {
        "mcpServers": {
            "test": {
                "transport": "stdio",
                "command": "echo",
                "args": ["hello"]
            }
        }
    }
    
    # Write test config
    config_path = Path("test_sync_config.json")
    with open(config_path, "w") as f:
        json.dump(test_config, f, indent=2)
    
    try:
        # Initialize MCP client
        client = MCPClient(config_file="test_sync_config.json")
        
        # Test loading configuration
        client.load_config()
        logger.info(f"Loaded {len(client.server_configs)} server configurations")
        
        for server_name, config in client.server_configs.items():
            logger.info(f"  - {server_name}: {config.transport} transport")
        
        logger.info("Configuration loading test completed successfully")
        
    except Exception as e:
        logger.error(f"Error testing sync client: {e}")
        logger.exception("Full traceback:")
    
    finally:
        # Clean up test config
        if config_path.exists():
            config_path.unlink()

if __name__ == "__main__":
    logger.info("Testing MCP client configuration loading...")
    test_sync_client()
    
    logger.info("\nTesting MCP client async initialization...")
    asyncio.run(test_mcp_client())

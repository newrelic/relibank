import logging
from typing import Any

from fastmcp import Client
from mcp.types import Tool

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

server_config = {
    "mcpServers": {
        "cloudflare": {
            "transport": "sse",
            "url": "https://docs.mcp.cloudflare.com/sse",
        },
    }
}

# https://mcp.deepwiki.com/sse

client = Client(server_config)


async def get_tools() -> list[Tool]:
    """
    Retrieve the list of tools from the MCP server.
    """
    async with client:
        tools = await client.list_tools()
        return tools


async def execute_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a tool on the MCP server with proper error handling.
    """
    try:
        result = await client.call_tool(tool_name, arguments)
        return result.data
    except Exception as e:
        logger.error(f"Error executing MCP tool {tool_name}: {e}")
        return {"error": f"Failed to execute tool {tool_name}"}


def convert_mcp_tools_to_openai_format(mcp_tools: list[Tool]) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI function calling format."""
    openai_functions = []

    for tool in mcp_tools:
        openai_function = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        openai_functions.append(openai_function)

    return openai_functions

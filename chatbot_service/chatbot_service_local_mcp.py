import asyncio
import os
import logging
import json
import httpx
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, AuthenticationError

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Global State ---
# The global client and readiness flag
client = None
is_ready = False
# The MCP endpoint is now a local URL since we're using a local server
mcp_endpoint = os.getenv("MCP_ENDPOINT_LOCAL")
model_id = "gpt-4o-mini" # A good choice for this type of application

# --- Helper Functions from Your Script ---
async def get_mcp_tools(mcp_url: str) -> List[Dict[str, Any]]:
    """Fetch available tools from MCP server with proper headers."""
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            # Use a POST request with a JSON-RPC payload for tool discovery
            response = await http_client.post(
                mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "tools_list_1",
                    "method": "tools/list",
                    "params": {}
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "OpenAI-MCP-Client/1.0"
                }
            )

            # Check for a successful HTTP status code
            response.raise_for_status()

            # Attempt to decode the JSON response
            try:
                data = response.json()
                if "result" in data and "tools" in data["result"]:
                    logger.info(f"Successfully fetched MCP tools from {mcp_url}.")
                    return data["result"]["tools"]
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response from {mcp_url}: {e}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching MCP tools from {mcp_url}: {e}")
        except Exception as e:
            logger.error(f"Error fetching MCP tools from {mcp_url}: {e}")

    logger.error("Failed to fetch MCP tools from configured endpoint.")
    return []


def convert_mcp_tools_to_openai_format(mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI function calling format."""
    openai_functions = []

    for tool in mcp_tools:
        openai_function = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
        }
        openai_functions.append(openai_function)

    return openai_functions


async def execute_mcp_tool(mcp_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool on the MCP server with proper error handling."""
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            # MCPs that support tool execution typically use a POST request
            endpoint = f"{mcp_url}"
            
            payload = {
                "jsonrpc": "2.0",
                "id": f"tool_call_{tool_name}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            response = await http_client.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "OpenAI-MCP-Client/1.0"
                }
            )

            response.raise_for_status()
            result = response.json()
            return result.get("result", {})

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing tool {tool_name} on {mcp_url}: {e}")
            return {"error": f"MCP server returned status {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name} on {mcp_url}: {e}")
            return {"error": f"Failed to execute tool {tool_name}"}


# --- FastAPI Application ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes the OpenAI client and checks for MCP server readiness.
    """
    global client, is_ready
    
    # Environment variable retrieval
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("BASE_URL")

    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set. Application will not start.")
        raise RuntimeError("OpenAI API key is required for startup.")

    try:
        # Initialize OpenAI client with the provided base URL
        client = AsyncOpenAI(api_key=openai_api_key, base_url=openai_base_url)
        is_ready = True
        logger.info("OpenAI client initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize OpenAI client: {e}. Application will not serve requests.")
        is_ready = False

    yield

    # Shutdown logic
    logger.info("Shutting down AI chatbot service.")
    if client:
        await client.close()
        logger.info("OpenAI client connection closed.")

app = FastAPI(
    title="Relibank AI Chatbot Service",
    description="Provides a conversational AI experience using OpenAI with MCP tools.",
    version="0.1.0",
    lifespan=lifespan
)

@app.post("/chat")
async def chat_with_model(prompt: str) -> Dict[str, Any]:
    """
    Chat with the OpenAI model and handle tool calls from an MCP server.
    """
    global client, is_ready, mcp_endpoint
    if not is_ready or not client:
        raise HTTPException(status_code=503, detail="AI service is not ready. Check logs for connection errors during startup.")

    try:
        logger.info(f"Received prompt: '{prompt}'")
        messages = [{"role": "user", "content": prompt}]
        
        # Get and convert MCP tools if an endpoint is configured
        openai_functions = []
        if mcp_endpoint:
            mcp_tools = await get_mcp_tools(mcp_endpoint)
            openai_functions = convert_mcp_tools_to_openai_format(mcp_tools)
            logger.info(f"Discovered {len(openai_functions)} MCP tools.")
            
        first_completion_params = {
            "model": model_id,
            "messages": messages,
        }

        if openai_functions:
            first_completion_params["tools"] = openai_functions
            first_completion_params["tool_choice"] = "auto"
        
        first_completion = await client.chat.completions.create(**first_completion_params)
        first_response_message = first_completion.choices[0].message
        
        # Handle tool calls
        if first_response_message.tool_calls and mcp_endpoint:
            messages.append(first_response_message)
            for tool_call in first_response_message.tool_calls:
                tool_output = await execute_mcp_tool(
                    mcp_endpoint,
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": json.dumps(tool_output)
                })

            # Get final response from model after tool execution
            second_completion = await client.chat.completions.create(
                model=model_id,
                messages=messages,
            )
            response_text = second_completion.choices[0].message.content
        else:
            response_text = first_response_message.content

        logger.info(f"Generated response: '{response_text}'")
        return {"response": response_text}

    except APIConnectionError as e:
        logger.error(f"Failed to connect to OpenAI API: {e}")
        raise HTTPException(status_code=503, detail="Failed to connect to OpenAI API.")
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating response.")

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    global is_ready
    if is_ready:
        return {"status": "healthy"}
    else:
        raise HTTPException(status_code=503, detail="AI service is not ready.")


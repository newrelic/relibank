import os
import logging
import json
import ssl
from contextlib import asynccontextmanager
from typing import Optional
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionToolMessageParam,
)
from pydantic import BaseModel
import newrelic.agent
from fastmcp import Client
from mcp.types import Tool
from utils.process_headers import process_headers

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

newrelic.agent.initialize('newrelic.ini', log_file='/app/newrelic.log', log_level=logging.DEBUG)

# --- Request/Response Models ---
class ChatResponse(BaseModel):
    response: str


class HealthResponse(BaseModel):
    status: str


# --- Global State ---
client: Optional[AsyncOpenAI] = None
is_ready: bool = False
MODEL_ID = "gpt-4.1"
AZURE_API_VERSION = "2023-05-15"


# --- MCP Code ---
server_config = {
    "mcpServers": {
        "cloudflare": {
            "transport": "sse",
            "url": "https://docs.mcp.cloudflare.com/sse",
        },
    }
}

# https://mcp.deepwiki.com/sse

# Create SSL context that doesn't verify certificates (for self-signed certs)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

try:
    mcp_client = Client(server_config, ssl_context=ssl_context)
except TypeError:
    # If Client doesn't accept ssl_context parameter, try without it
    logger.warning("Client does not support ssl_context parameter, proceeding without SSL verification override")
    mcp_client = Client(server_config)

async def get_tools() -> list[Tool]:
    """
    Retrieve the list of tools from the MCP server.
    """
    async with mcp_client:
        tools = await mcp_client.list_tools()
        return tools


async def execute_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a tool on the MCP server with proper error handling.
    """
    try:
        result = await mcp_client.call_tool(tool_name, arguments)
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
    openai_base_url = os.getenv("OPENAI_BASE_URL")

    # TODO remove this if it's not needed
    #OPENAI_BASE_URL="https://nerd-completion.staging-service.nr-ops.net"
    # OPENAI_BASE_URL="https://stg-green-smoothie-east-us-2.openai.azure.com/openai/v1"


    if not openai_api_key or not openai_base_url:
        logger.error("OPENAI_API_KEY or OPENAI_BASE_URL environment variable not set. Application will not start.")
        raise RuntimeError("OpenAI API key and base url are required for startup.")

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
    lifespan=lifespan,
)

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.post("/chatbot-service/chat", response_model=ChatResponse)
async def chat_with_model(prompt: str, request: Request) -> ChatResponse:
    """
    Chat with the OpenAI model and handle tool calls from an MCP server.
    """
    if not is_ready or not client:
        raise HTTPException(
            status_code=503,
            detail="AI service is not ready. Check logs for connection errors during startup.",
        )

    try:
        logger.info(f"Received prompt: '{prompt}'")
        messages: list[ChatCompletionMessageParam] = [ChatCompletionUserMessageParam(content=prompt, role="user")]

        # Get and convert MCP tools
        openai_functions = []
        try:
            mcp_tools = await get_tools()
            openai_functions = convert_mcp_tools_to_openai_format(mcp_tools)
            logger.info(f"Discovered {len(openai_functions)} MCP tools.")
        except Exception as e:
            logger.error(f"Failed to discover MCP tools: {e}")

        # Prepare completion parameters
        completion_params = {
            "model": MODEL_ID,
            "messages": messages,
        }

        if openai_functions:
            completion_params["tools"] = openai_functions
            completion_params["tool_choice"] = "auto"

        # Get initial response from model
        first_completion = await client.chat.completions.create(**completion_params)
        first_response_message = first_completion.choices[0].message

        # Handle tool calls if present
        if first_response_message.tool_calls:
            messages.append(first_response_message)

            for tool_call in first_response_message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    tool_output = await execute_mcp_tool(tool_call.function.name, arguments)
                    messages.append(
                        ChatCompletionToolMessageParam(
                            content=json.dumps(tool_output),
                            tool_call_id=tool_call.id,
                            role="tool",
                        )
                    )
                    process_headers(dict(request.headers))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {e}")
                    messages.append(
                        ChatCompletionToolMessageParam(
                            content=json.dumps({"error": "Invalid tool arguments"}),
                            tool_call_id=tool_call.id,
                            role="tool",
                        )
                    )

            # Get final response from model after tool execution
            second_completion = await client.chat.completions.create(
                model=MODEL_ID,
                messages=messages,
            )
            response_text = second_completion.choices[0].message.content
        else:
            response_text = first_response_message.content

        if not response_text:
            response_text = "I apologize, but I couldn't generate a response. Please try again."

        logger.info(f"Generated response: '{response_text}'")
        return ChatResponse(response=response_text)

    except APIConnectionError as e:
        logger.error(f"Failed to connect to OpenAI API: {e}")
        raise HTTPException(status_code=503, detail="Failed to connect to OpenAI API.")
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating response.")

@app.get("/chatbot-service/")
async def ok():
    """Root return 200"""
    return "ok"

@app.get("/chatbot-service/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health check endpoint."""
    return {"status": "healthy"}

# @app.get("/health", response_model=HealthResponse)
# async def health_check() -> HealthResponse:
#     """Simple health check endpoint."""
#     if is_ready:
#         return HealthResponse(status="healthy")
#     else:
#         raise HTTPException(status_code=503, detail="AI service is not ready.")

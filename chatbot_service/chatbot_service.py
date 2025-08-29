import os
import logging
import json
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError

from .mcp_client import get_tools, execute_mcp_tool, convert_mcp_tools_to_openai_format

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
# The MCP endpoint is now a global variable to be set during lifespan
model_id = "gpt-4o-mini" # A good choice for this type of application


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
async def chat_with_model(prompt: str) -> dict[str, Any]:
    """
    Chat with the OpenAI model and handle tool calls from an MCP server.
    """
    if not is_ready or not client:
        raise HTTPException(status_code=503, detail="AI service is not ready. Check logs for connection errors during startup.")

    try:
        logger.info(f"Received prompt: '{prompt}'")
        messages = [{"role": "user", "content": prompt}]

        # Get and convert MCP tools if an endpoint is configured
        openai_functions = []
        try:
            mcp_tools = await get_tools()
            openai_functions = convert_mcp_tools_to_openai_format(mcp_tools)
            logger.info(f"Discovered {len(openai_functions)} MCP tools.")
        except Exception as e:
            logger.error(f"Failed to discover MCP tools: {e}")

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

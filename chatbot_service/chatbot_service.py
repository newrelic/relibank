import os
import logging
import json
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionToolMessageParam,
)
from pydantic import BaseModel

from mcp_client import get_tools, execute_mcp_tool, convert_mcp_tools_to_openai_format

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Request/Response Models ---
class ChatResponse(BaseModel):
    response: str


class HealthResponse(BaseModel):
    status: str


# --- Global State ---
client: Optional[AsyncOpenAI] = None
is_ready: bool = False
MODEL_ID = "gpt-4o-mini"  # Use constant naming convention


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
    lifespan=lifespan,
)


@app.post("/chat", response_model=ChatResponse)
async def chat_with_model(prompt: str) -> ChatResponse:
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


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health check endpoint."""
    if is_ready:
        return HealthResponse(status="healthy")
    else:
        raise HTTPException(status_code=503, detail="AI service is not ready.")

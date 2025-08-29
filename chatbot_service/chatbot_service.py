import os
import logging
import json
from contextlib import asynccontextmanager
from typing import Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam, ChatCompletionToolMessageParam

from mcp_client import get_tools, execute_mcp_tool, convert_mcp_tools_to_openai_format

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatbotService:
    """Service class to manage OpenAI client and chatbot functionality."""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model_id = "gpt-4o-mini"
        self.is_ready = False

    async def initialize(self):
        """Initialize the OpenAI client."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("BASE_URL")

        if not openai_api_key:
            logger.error("OPENAI_API_KEY environment variable not set.")
            raise RuntimeError("OpenAI API key is required for startup.")

        try:
            self.client = AsyncOpenAI(api_key=openai_api_key, base_url=openai_base_url)
            self.is_ready = True
            logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize OpenAI client: {e}")
            self.is_ready = False
            raise

    async def shutdown(self):
        """Clean shutdown of the service."""
        if self.client:
            await self.client.close()
            logger.info("OpenAI client connection closed.")

    def check_readiness(self):
        """Check if the service is ready to handle requests."""
        if not self.is_ready or not self.client:
            raise HTTPException(
                status_code=503,
                detail="AI service is not ready. Check logs for connection errors during startup."
            )

    async def simple_chat(self, prompt: str) -> str:
        """Simple chat without MCP tools."""
        self.check_readiness()

        try:
            messages: List[ChatCompletionMessageParam] = [
                ChatCompletionUserMessageParam(role="user", content=prompt)
            ]

            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in simple chat: {e}")
            raise HTTPException(status_code=500, detail="Error generating response.")

    async def chat_with_tools(self, prompt: str) -> str:
        """Chat with MCP tools support."""
        self.check_readiness()

        try:
            logger.info(f"Received prompt: '{prompt}'")
            messages: List[ChatCompletionMessageParam] = [
                ChatCompletionUserMessageParam(role="user", content=prompt)
            ]

            # Get and convert MCP tools
            openai_functions = []
            try:
                mcp_tools = await get_tools()
                openai_functions = convert_mcp_tools_to_openai_format(mcp_tools)
                logger.info(f"Discovered {len(openai_functions)} MCP tools.")
            except Exception as e:
                logger.error(f"Failed to discover MCP tools: {e}")

            first_completion_params = {
                "model": self.model_id,
                "messages": messages,
            }

            if openai_functions:
                first_completion_params["tools"] = openai_functions
                first_completion_params["tool_choice"] = "auto"

            first_completion = await self.client.chat.completions.create(**first_completion_params)
            first_response_message = first_completion.choices[0].message

            # Handle tool calls
            if first_response_message.tool_calls:
                # Add the assistant's response with tool calls
                # Convert tool calls to the proper format for message parameters
                tool_calls_for_message = []
                for tool_call in first_response_message.tool_calls:
                    tool_calls_for_message.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })

                messages.append(ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=first_response_message.content,
                    tool_calls=tool_calls_for_message
                ))

                for tool_call in first_response_message.tool_calls:
                    tool_output = await execute_mcp_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    messages.append(ChatCompletionToolMessageParam(
                        tool_call_id=tool_call.id,
                        role="tool",
                        content=json.dumps(tool_output)
                    ))

                # Get final response from model after tool execution
                second_completion = await self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                )
                response_text = second_completion.choices[0].message.content
            else:
                response_text = first_response_message.content

            logger.info(f"Generated response: '{response_text}'")
            return response_text

        except APIConnectionError as e:
            logger.error(f"Failed to connect to OpenAI API: {e}")
            raise HTTPException(status_code=503, detail="Failed to connect to OpenAI API.")
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid OpenAI API key.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error generating response.")


# Create a single instance of the service
chatbot_service = ChatbotService()


# --- Dependency injection ---
async def get_chatbot_service() -> ChatbotService:
    """Dependency to get the chatbot service instance."""
    return chatbot_service


# --- FastAPI Application ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager to handle startup and shutdown events."""
    try:
        await chatbot_service.initialize()
    except Exception as e:
        logger.critical(f"Failed to initialize service: {e}")
        raise

    yield

    await chatbot_service.shutdown()
    logger.info("Shutting down AI chatbot service.")


app = FastAPI(
    title="Relibank AI Chatbot Service",
    description="Provides a conversational AI experience using OpenAI with MCP tools.",
    version="0.1.0",
    lifespan=lifespan
)


@app.post("/chatresponse")
async def chat_response_test(
    prompt: str,
    service: ChatbotService = Depends(get_chatbot_service)
) -> dict[str, Any]:
    """Test endpoint for basic chat functionality without MCP tools."""
    response = await service.simple_chat(prompt)
    return {"response": response}


@app.post("/chat")
async def chat_with_model(
    prompt: str,
    service: ChatbotService = Depends(get_chatbot_service)
) -> dict[str, Any]:
    """Chat with the OpenAI model and handle tool calls from an MCP server."""
    response = await service.chat_with_tools(prompt)
    return {"response": response}


@app.get("/health")
async def health_check(
    service: ChatbotService = Depends(get_chatbot_service)
):
    """Simple health check endpoint."""
    if service.is_ready:
        return {"status": "healthy"}
    else:
        raise HTTPException(status_code=503, detail="AI service is not ready.")

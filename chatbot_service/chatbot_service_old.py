import asyncio
import os
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai import APIConnectionError, APIStatusError, AuthenticationError
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the base_url from environment variables
base_url = os.getenv("BASE_URL")

# --- MCP Tool Definition and Implementation ---

DEEPWIKI_MCP_URL = "https://mcp.deepwiki.com/mcp"

# A dictionary to map tool names to their corresponding Python functions.
AVAILABLE_TOOLS = {}

async def deepwiki_fetch(url: str, mode: str, question: str = None) -> str:
    """
    Fetches content from a DeepWiki knowledge base.
    """
    logger.info(f"Tool call: deepwiki_fetch with url='{url}' and mode='{mode}'")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    # Correct payload structure based on your documentation snippet
    request_params = {
        "url": url,
        "mode": mode,
    }
    if question:
        request_params["query"] = question
        
    payload = {
        "action": "deepwiki_fetch",
        "params": request_params
    }
    
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(DEEPWIKI_MCP_URL, headers=headers, json=payload, timeout=30.0)
            
            # The DeepWiki server returns a 200 even for an error response, so we check the JSON payload.
            data = response.json()
            if data.get("status") == "error":
                return f"Error from MCP: {data.get('message', 'Unknown error')}"
            
            response.raise_for_status()
            
            # Return the full JSON response for the model to parse
            return json.dumps(data)
            
    except httpx.HTTPStatusError as e:
        return f"Error: Failed to retrieve data from DeepWiki. API returned status {e.response.status_code}."
    except Exception as e:
        return f"Error: An unexpected error occurred while fetching data from DeepWiki: {e}."

# Mapping of tool names to their handler functions
AVAILABLE_TOOLS["deepwiki_fetch"] = deepwiki_fetch

# --- Main Application Logic ---

# Global client and readiness flag
client = None
is_ready = False
model_id = "gpt-4o-mini"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes the OpenAI client and checks for readiness.
    """
    global client, is_ready

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set. Application will not start.")
        raise RuntimeError("OpenAI API key is required for startup.")

    logger.info("Initializing OpenAI client...")
    client = AsyncOpenAI(api_key=openai_api_key, base_url=base_url)

    if client:
        logger.info("OpenAI client initialized successfully.")
        is_ready = True
    else:
        logger.critical("Failed to initialize OpenAI client. Application will not be able to serve chat requests.")
        is_ready = False

    yield

    logger.info("Shutting down AI chatbot service.")
    if client:
        await client.close()
        logger.info("OpenAI client connection closed.")

app = FastAPI(
    title="Relibank AI Chatbot Service",
    description="Provides a conversational AI experience using OpenAI.",
    version="0.1.0",
    lifespan=lifespan
)

@app.post("/chat")
async def chat_with_model(prompt: str):
    """
    Chat with the OpenAI model and handle tool calls.
    """
    global client, is_ready
    if not is_ready:
        raise HTTPException(status_code=503, detail="AI service is not ready. Check logs for connection errors during startup.")

    messages = [
        {"role": "system", "content": "You are Relibank's helpful AI assistant."},
        {"role": "user", "content": prompt}
    ]

    try:
        logger.info(f"Received prompt: '{prompt}'")
        
        first_completion = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "deepwiki_fetch",
                        "description": "Fetches content from a DeepWiki knowledge base. Can be used to ask a question or retrieve the wiki's structure. Requires a valid DeepWiki URL.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The full DeepWiki URL of the repository to query (e.g., 'https://deepwiki.com/user/repo').",
                                },
                                "mode": {
                                    "type": "string",
                                    "description": "The output mode, either 'aggregate' for a single Markdown document or 'pages' for structured page data.",
                                    "enum": ["aggregate", "pages"]
                                },
                                "question": {
                                    "type": "string",
                                    "description": "A specific question to ask the knowledge base. Only used when mode is 'aggregate'."
                                }
                            },
                            "required": ["url", "mode"]
                        }
                    },
                }
            ],
            tool_choice="auto",
        )

        first_response_message = first_completion.choices[0].message
        
        if first_response_message.tool_calls:
            messages.append(first_response_message)
            tool_call_results = []

            for tool_call in first_response_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                if function_name in AVAILABLE_TOOLS:
                    tool_function = AVAILABLE_TOOLS[function_name]
                    tool_output = await tool_function(**arguments)
                    tool_call_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_output,
                    })
                else:
                    tool_call_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error: Tool '{function_name}' not found."
                    })

            messages.extend(tool_call_results)
            
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
    except APIStatusError as e:
        logger.error(f"OpenAI API returned an error: {e.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.status_code, detail="OpenAI API error.")
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

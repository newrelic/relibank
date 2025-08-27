import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai import APIConnectionError, APIStatusError, AuthenticationError
import httpx


# Configure logging to be a bit more detailed
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global client and readiness flag
client = None
is_ready = False
model_id = "gpt-4o-mini"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes the OpenAI client and waits for a successful connection.
    """
    global client, is_ready
    
    # Get the OpenAI API key from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set. Application will not start.")
        raise RuntimeError("OpenAI API key is required for startup.")

    # Retry logic for client initialization
    max_retries = 5
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Initializing OpenAI client...")
            
            # Create an asynchronous httpx client that explicitly disables proxies
            http_client = httpx.AsyncClient(proxies=None, timeout=30.0)
            client = AsyncOpenAI(api_key=openai_api_key, http_client=http_client)

            # Wait for a successful connection to validate the client
            # The health check is a good way to test this
            # We will perform a simple list models call to verify connection
            # Note: A real health check might check more than just the client existence.
            logger.info("Testing OpenAI client connection...")
            await client.models.list()
            logger.info("OpenAI client initialized and connected successfully.")
            is_ready = True
            break  # Exit the loop on success
        except Exception as e:
            logger.error(f"Failed to initialize or connect to OpenAI API: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.critical("Maximum retries reached. Application will not be able to serve chat requests.")
                is_ready = False
    
    yield

    # Shutdown logic
    logger.info("Shutting down AI chatbot service.")
    if client:
        # Gracefully close the aiohttp session used by the client
        await client.close()
        logger.info("OpenAI client connection closed.")

# FastAPI app instance with lifespan
app = FastAPI(
    title="Relibank AI Chatbot Service",
    description="Provides a conversational AI experience using OpenAI.",
    version="0.1.0",
    lifespan=lifespan
)

@app.post("/chat")
async def chat_with_model(prompt: str):
    """
    Chat with the OpenAI model.
    """
    global client, is_ready
    if not is_ready:
        raise HTTPException(status_code=503, detail="AI service is not ready. Check logs for connection errors during startup.")
    
    try:
        logger.info(f"Received prompt: '{prompt}'")
        
        completion: ChatCompletion = await client.chat.completions.create(
            model=model_id, # Using a cost-effective model
            messages=[
                {"role": "system", "content": "You are Relibank's helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "text"},
            temperature=0.7
        )
        response_text = completion.choices[0].message.content

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

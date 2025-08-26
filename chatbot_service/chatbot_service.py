import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai import APIConnectionError, APIStatusError, AuthenticationError
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global OpenAI client instance
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Initializes the OpenAI client.
    """
    global client
    
    # Get the OpenAI API key from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logging.error("OPENAI_API_KEY environment variable not set.")
        raise RuntimeError("OpenAI API key is required for startup.")

    try:
        logging.info("Initializing OpenAI client...")
        # Create an asynchronous httpx client that explicitly disables proxies
        http_client = httpx.AsyncClient(proxies=None)
        client = AsyncOpenAI(api_key=openai_api_key, http_client=http_client)
        logging.info("OpenAI client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        raise RuntimeError("Failed to initialize OpenAI client during startup.")
    
    yield

    # Shutdown logic
    logging.info("Shutting down AI chatbot service.")
    if client:
        await client.close()
        logging.info("OpenAI client connection closed.")

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
    global client
    if not client:
        raise HTTPException(status_code=503, detail="AI service is not ready.")
    
    try:
        logging.info(f"Received prompt: '{prompt}'")
        
        completion: ChatCompletion = await client.chat.completions.create(
            model="gpt-4o-mini", # Using a cost-effective model
            messages=[
                {"role": "system", "content": "You are Relibank's helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "text"},
            temperature=0.7
        )
        response_text = completion.choices[0].message.content

        logging.info(f"Generated response: '{response_text}'")
        
        return {"response": response_text}

    except APIConnectionError as e:
        logging.error(f"Failed to connect to OpenAI API: {e}")
        raise HTTPException(status_code=503, detail="Failed to connect to OpenAI API.")
    except AuthenticationError as e:
        logging.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key.")
    except APIStatusError as e:
        logging.error(f"OpenAI API returned an error: {e.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.status_code, detail="OpenAI API error.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Error generating response.")

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

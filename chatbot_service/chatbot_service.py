import asyncio
import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import time
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global tokenizer and model
tokenizer = None
model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to handle startup and shutdown events.
    Loads the Mistral model and tokenizer.
    """
    global tokenizer, model
    
    # Check for CPU or GPU availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Using device: {device}")

    # The model we are going to use
    model_id = "mistralai/Mistral-7B-Instruct-v0.3"
    
    # Hugging Face access token (you need to provide this in docker-compose.yml)
    hf_token = os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        logging.error("HUGGING_FACE_HUB_TOKEN environment variable not set.")
        raise RuntimeError("Hugging Face access token is required to download the model.")

    try:
        logging.info(f"Loading tokenizer and model: {model_id}")
        tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(model_id, token=hf_token).to(device)
        logging.info("Model and tokenizer loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load model: {e}")
        raise RuntimeError("Failed to load model during startup.")
    
    yield

    # Shutdown logic
    logging.info("Shutting down AI chatbot service.")

# FastAPI app instance with lifespan
app = FastAPI(
    title="Relibank AI Chatbot Service",
    description="Provides a conversational AI experience using Mistral.",
    version="0.1.0",
    lifespan=lifespan
)

@app.post("/chat")
async def chat_with_model(prompt: str):
    """
    Chat with the AI model.
    """
    global tokenizer, model
    if not tokenizer or not model:
        raise HTTPException(status_code=503, detail="AI model is not ready.")
    
    try:
        # Simple tokenization and generation for a demo
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(**inputs, max_length=100)
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        logging.info(f"Received prompt: '{prompt}'")
        logging.info(f"Generated response: '{response_text}'")
        
        return {"response": response_text}
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail="Error generating response.")

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

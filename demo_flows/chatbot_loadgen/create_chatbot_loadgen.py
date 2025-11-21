import requests
import random
import json
import argparse
import sys
import os

QUESTION_FILE = "questions.txt"

def get_random_question() -> str:
    if not os.path.exists(QUESTION_FILE):
        raise FileNotFoundError(f"Error: The question file '{QUESTION_FILE}' was not found in the current directory.")

    with open(QUESTION_FILE, 'r') as f:
        # Read all non-empty, stripped lines into a list
        questions = [line.strip() for line in f if line.strip()]

    if not questions:
        raise ValueError(f"Error: The question file '{QUESTION_FILE}' is empty or contains no valid questions.")
        
    return random.choice(questions)

def post_random_question(api_url: str):
    """
    Selects a random question and POSTs it to the chatbot API endpoint.
    args:
        api_url: The full URL of the chatbot's /chat endpoint.
    """
    # Select a random question
    random_question = get_random_question()
    print(f"Selected Question: '{random_question}'")
    params = {
        "prompt": random_question
    }

    print(f"Sending POST request to: {api_url}")

    try:
        response = requests.post(api_url, params=params)
        response.raise_for_status()
        response_data = response.json()
        chatbot_response = response_data.get("response", "No response field found.")

        print(f"Status Code: {response.status_code}")
        print(f"Chatbot Response: {chatbot_response}")

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred during the API call: {e}")
        if 'response' in locals() and response.content:
             print(f"Error Details (Raw): {response.content.decode()}")
        sys.exit(1)

if __name__ == "__main__":
    # Initialize the argument parser
    parser = argparse.ArgumentParser(
        description="Send a random question to the chatbot API endpoint.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'api_url',
        type=str,
        help="The full URL of the chatbot's /chat endpoint (e.g., http://127.0.0.1:8000/chatbot-service/chat)"
    )

    args = parser.parse_args()

    post_random_question(args.api_url)
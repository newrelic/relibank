import requests
import random
import json
import argparse
import sys
import os
import time

QUESTION_FILE = "specialist_questions.txt"

def get_random_specialist_question() -> str:
    """Load a random question that triggers specialist delegation"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    question_path = os.path.join(script_dir, QUESTION_FILE)

    if not os.path.exists(question_path):
        raise FileNotFoundError(f"Error: The question file '{QUESTION_FILE}' was not found at {question_path}")

    with open(question_path, 'r') as f:
        questions = [line.strip() for line in f if line.strip()]

    if not questions:
        raise ValueError(f"Error: The question file '{QUESTION_FILE}' is empty or contains no valid questions.")

    return random.choice(questions)

def post_specialist_question(api_url: str):
    """
    Selects a random specialist question and POSTs it to the chatbot API endpoint.
    These questions will trigger specialist delegation with the 8-second delay.

    args:
        api_url: The full URL of the chatbot's /chat endpoint.
    """
    random_question = get_random_specialist_question()
    print(f"Selected Specialist Question: '{random_question}'")
    params = {
        "prompt": random_question
    }

    print(f"Sending POST request to: {api_url}")
    start_time = time.time()

    try:
        response = requests.post(api_url, params=params, timeout=30)
        elapsed = time.time() - start_time
        response.raise_for_status()
        response_data = response.json()
        chatbot_response = response_data.get("response", "No response field found.")

        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.2f}s")
        print(f"Chatbot Response: {chatbot_response[:200]}...")  # Truncate long responses

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"\nRequest timed out after {elapsed:.2f}s")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        print(f"\nAn error occurred during the API call after {elapsed:.2f}s: {e}")
        if 'response' in locals() and response.content:
             print(f"Error Details (Raw): {response.content.decode()}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send specialist questions to the chatbot API endpoint (triggers 8s delay).",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'api_url',
        type=str,
        help="The full URL of the chatbot's /chat endpoint (e.g., http://relibank.westus2.cloudapp.azure.com/chatbot-service/chat)"
    )

    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help="Number of requests to send (default: 1)"
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0,
        help="Delay in seconds between requests (default: 0)"
    )

    args = parser.parse_args()

    print(f"Sending {args.count} specialist question(s) to chatbot...")
    for i in range(args.count):
        if i > 0 and args.delay > 0:
            print(f"\nWaiting {args.delay}s before next request...")
            time.sleep(args.delay)

        print(f"\n--- Request {i+1}/{args.count} ---")
        post_specialist_question(args.api_url)

    print(f"\nCompleted {args.count} specialist request(s)")

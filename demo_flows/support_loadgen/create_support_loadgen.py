import requests
import random
import json
import argparse
import sys
import os

QUESTION_FILE = "questions.txt"
PROBLEM_QUESTION_FILE = "problem_questions.txt"

# Odds of drawing from PROBLEM_QUESTION_FILE instead of QUESTION_FILE on any
# given request. Keeps the problem/adversarial prompts (token-limit-breaking,
# prompt-injection, PII exfiltration, bias-baiting, etc.) showing up often
# enough to reliably surface within a demo session, without every request
# being adversarial.
PROBLEM_QUESTION_RATE = 0.25

def _load_questions(path: str) -> list[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Error: The question file '{path}' was not found in the current directory.")

    with open(path, 'r') as f:
        # Read all non-empty, stripped lines into a list
        questions = [line.strip() for line in f if line.strip()]

    if not questions:
        raise ValueError(f"Error: The question file '{path}' is empty or contains no valid questions.")

    return questions

def get_random_question(force_problem: bool = False) -> str:
    source_file = PROBLEM_QUESTION_FILE if force_problem or random.random() < PROBLEM_QUESTION_RATE else QUESTION_FILE
    questions = _load_questions(source_file)
    return random.choice(questions)

def post_random_question(api_url: str, force_problem: bool = False):
    """
    Selects a random question and POSTs it to the support service API endpoint.
    args:
        api_url: The full URL of the support service's /chat endpoint.
        force_problem: If True, always draw from PROBLEM_QUESTION_FILE.
    """
    # Select a random question
    random_question = get_random_question(force_problem=force_problem)
    print(f"Selected Question: '{random_question}'")
    params = {
        "prompt": random_question
    }

    print(f"Sending POST request to: {api_url}")

    try:
        response = requests.post(api_url, params=params)
        response.raise_for_status()
        response_data = response.json()
        support_response = response_data.get("response", "No response field found.")

        print(f"Status Code: {response.status_code}")
        print(f"Support Response: {support_response}")

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred during the API call: {e}")
        if 'response' in locals() and response.content:
             print(f"Error Details (Raw): {response.content.decode()}")
        sys.exit(1)

if __name__ == "__main__":
    # Initialize the argument parser
    parser = argparse.ArgumentParser(
        description="Send a random question to the support service API endpoint.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'api_url',
        type=str,
        help="The full URL of the support service's /chat endpoint (e.g., http://127.0.0.1:8000/support-service/chat)"
    )

    parser.add_argument(
        '--force-problem',
        action='store_true',
        help="Always draw the question from problem_questions.txt instead of the normal random mix."
    )

    args = parser.parse_args()

    post_random_question(args.api_url, force_problem=args.force_problem)
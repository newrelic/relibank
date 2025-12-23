import requests
import json
import sys

# --- Configuration ---
BASE_URL = sys.argv[1] or "http://localhost:8000"
SCENARIO_NAME = "relibank-bill-pay-resilience-test"

# Full URL for the API endpoint
API_ENDPOINT = f"{BASE_URL}/scenario-runner/api/trigger_chaos/{SCENARIO_NAME}"

def trigger_chaos_mesh_job():
    """
    HITS the /scenario-runner/api/trigger_chaos/{scenario_name} endpoint
    to trigger the Chaos Mesh job defined in the FastAPI service.
    """
    print("--- Chaos Mesh Job Trigger ---")
    print(f"Target URL: {API_ENDPOINT}")
    print(f"Scenario:   {SCENARIO_NAME}")
    
    try:
        # The endpoint expects a POST request with no body for this action
        response = requests.post(API_ENDPOINT)
        
        # Raise an HTTPError if the response status code is 4xx or 5xx
        response.raise_for_status() 

        # Attempt to parse the JSON response
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            print("\nError: Received non-JSON response from server.")
            print(f"Status Code: {response.status_code}")
            print(f"Raw Response: {response.text}")
            return

        # Check the 'status' field in the JSON response
        if result.get("status") == "success":
            print("\nSuccess!")
            print(f"Message: {result.get('message')}")
        elif result.get("status") == "warning":
            print("\nWarning: Chaos experiment may not have executed properly!")
            print(f"Message: {result.get('message')}")
            print("\nThis usually means:")
            print("  - Chaos Mesh is not installed or not running")
            print("  - No pods matched the selector")
            print("  - The experiment was created but not processed")
            sys.exit(1)
        elif result.get("error"):
            print("\nError from Scenario Runner!")
            print(f"Error: {result.get('error')}")
            sys.exit(1)
        elif result.get("status") == "error":
             print("\nError during Kubernetes API Call!")
             print(f"Message: {result.get('message')}")
             sys.exit(1)
        else:
            print("\nUnknown Response Format!")
            print(json.dumps(result, indent=4))
            sys.exit(1)


    except requests.exceptions.ConnectionError:
        print(f"\nConnection Error: Could not connect to the API at {BASE_URL}")
        print("Please ensure the 'scenario service.py' is running and the BASE_URL is correct.")
        sys.exit(1)
    except requests.exceptions.HTTPError as err:
        print(f"\nHTTP Error occurred: {err}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    trigger_chaos_mesh_job()
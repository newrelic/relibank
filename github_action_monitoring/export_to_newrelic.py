import os
import json
import urllib.request
import urllib.error
import sys
import time

def main():
    """
    Reads GitHub Actions context and New Relic secrets from environment variables,
    prepares a log payload, and posts it to the New Relic Log API.
    """
    
    # --- 1. Gather Context from Environment Variables ---
    JOB_STATUS = os.environ.get('JOB_STATUS')
    JOB_NAME = os.environ.get('JOB_NAME')
    RUN_ID = os.environ.get('RUN_ID')
    REPOSITORY = os.environ.get('REPOSITORY')
    SERVER_URL = os.environ.get('SERVER_URL')
    WORKFLOW = os.environ.get('WORKFLOW')

    NR_LICENSE_KEY = os.environ.get('NR_LICENSE_KEY')
    NR_ACCOUNT_ID = os.environ.get('NR_ACCOUNT_ID')
    NR_ENDPOINT_BASE = os.environ.get('NR_ENDPOINT_BASE')
    ENVIRONMENT = os.environ.get('ENVIRONMENT')
    FAILING_STEP_NAME = os.environ.get('FAILING_STEP_NAME', 'N/A') # Read the new variable

    # Quick check for critical New Relic credentials
    if not (NR_LICENSE_KEY and NR_ACCOUNT_ID and NR_ENDPOINT_BASE):
        print("::error::New Relic configuration missing. Exiting Python script.")
        sys.exit(1)
        
    # --- 2. Prepare Payload (Log API Format) ---
    
    # Construct the direct URL to the GitHub Actions run logs
    RUN_URL = f"{SERVER_URL}/{REPOSITORY}/actions/runs/{RUN_ID}"
    
    # The Log API URL is fixed, not dependent on Account ID in the path
    NR_ENDPOINT = NR_ENDPOINT_BASE 

    failure_reason = "N/A"
    if JOB_STATUS == "failure":
        # Enhanced failure reason using the detected failing step name
        failure_reason = f"Job failed in step: '{FAILING_STEP_NAME}'. Use the 'runUrl' link to view full logs."
        LEVEL = "error"
    else:
        LEVEL = "info"

    # Log API expects a structure for log events
    log_entry = {
        # Updated message to include ENVIRONMENT and JOB_NAME
        "message": f"GitHub Actions job '{JOB_NAME}' environment '{ENVIRONMENT}' on workflow '{WORKFLOW}' completed with status: {JOB_STATUS}",
        "attributes": {
            "level": LEVEL,
            "logType": "GitHubActionsStatus",
            "jobStatus": JOB_STATUS,
            "jobName": JOB_NAME,
            "workflowName": WORKFLOW,
            "failingStepName": FAILING_STEP_NAME,
            "environment": ENVIRONMENT,
            "runUrl": RUN_URL,
            "accountId": NR_ACCOUNT_ID,
            "repository": REPOSITORY,
            "failureReason": failure_reason
        }
    }

    # Log API expects an array of log entries
    payload = json.dumps([log_entry]).encode('utf-8')

    print(f"Constructed RUN_URL: {RUN_URL}") 
    print(f"Failing Step Detected: {FAILING_STEP_NAME}")

    # --- 3. Send Request ---
    print(f"Sending log payload for workflow '{WORKFLOW}' to New Relic Log API...")

    try:
        req = urllib.request.Request(
            url=NR_ENDPOINT, 
            data=payload,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                # Log API requires X-License-Key, which is the value of your NR_LICENSE_KEY secret
                'X-License-Key': NR_LICENSE_KEY 
            }
        )
        
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            if status not in (200, 202):
                print(f"::error::New Relic Log API returned unexpected status code {status}")
                print(f"Response Body: {response.read().decode('utf-8')}")
                sys.exit(1)
            else:
                print(f"Status log event successfully sent to New Relic. Response code: {status}")
                
    except urllib.error.HTTPError as e:
        print(f"::error::HTTP Error during API call: {e.code} - {e.reason}")
        # Log API sometimes returns helpful error messages in the body
        try:
            print(f"Response Body: {e.read().decode()}")
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"::error::An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

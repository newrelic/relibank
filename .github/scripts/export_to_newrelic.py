import os
import json
import urllib.request
import urllib.error
import sys


def main():
    # --- 1. Gather context from environment ---
    JOB_STATUS = os.environ.get('JOB_STATUS')
    JOB_NAME = os.environ.get('JOB_NAME')
    RUN_ID = os.environ.get('RUN_ID')
    REPOSITORY = os.environ.get('REPOSITORY')
    SERVER_URL = os.environ.get('SERVER_URL')
    WORKFLOW = os.environ.get('WORKFLOW')
    FAILING_STEP_NAME = os.environ.get('FAILING_STEP_NAME', 'N/A')

    ENVIRONMENT = os.environ.get('ENVIRONMENT')
    SERVICE = os.environ.get('SERVICE')
    TARGET_COLOR = os.environ.get('TARGET_COLOR')
    RUN_MODE = os.environ.get('RUN_MODE', 'live')
    REPLICAS_BEFORE = os.environ.get('REPLICAS_BEFORE')
    REPLICAS_AFTER = os.environ.get('REPLICAS_AFTER')

    NR_LICENSE_KEY = os.environ.get('NR_LICENSE_KEY')
    NR_ACCOUNT_ID = os.environ.get('NR_ACCOUNT_ID')
    NR_ENDPOINT = os.environ.get('NR_ENDPOINT_BASE')

    if not (NR_LICENSE_KEY and NR_ACCOUNT_ID and NR_ENDPOINT):
        print("::error::New Relic configuration missing. Exiting.")
        sys.exit(1)

    # --- 2. Build payload ---
    RUN_URL = f"{SERVER_URL}/{REPOSITORY}/actions/runs/{RUN_ID}"

    if JOB_STATUS == "failure":
        failure_reason = f"Job failed in step: '{FAILING_STEP_NAME}'. See: {RUN_URL}"
        level = "error"
    else:
        failure_reason = "N/A"
        level = "info"

    log_entry = {
        "message": (
            f"scaling-demo: {SERVICE} scaled {REPLICAS_BEFORE} → {REPLICAS_AFTER} replicas "
            f"in {ENVIRONMENT}/{TARGET_COLOR} — {JOB_STATUS}"
        ),
        "attributes": {
            "level": level,
            "logType": "GitHubActionsStatus",
            "jobStatus": JOB_STATUS,
            "jobName": JOB_NAME,
            "workflowName": WORKFLOW,
            "failingStepName": FAILING_STEP_NAME,
            "environment": ENVIRONMENT,
            "service": SERVICE,
            "targetColor": TARGET_COLOR,
            "runMode": RUN_MODE,
            "replicasBefore": REPLICAS_BEFORE,
            "replicasAfter": REPLICAS_AFTER,
            "runUrl": RUN_URL,
            "accountId": NR_ACCOUNT_ID,
            "repository": REPOSITORY,
            "failureReason": failure_reason,
        },
    }

    payload = json.dumps([log_entry]).encode('utf-8')
    print(f"Sending scaling result for {SERVICE} to New Relic Log API...")

    # --- 3. Send ---
    try:
        req = urllib.request.Request(
            url=NR_ENDPOINT,
            data=payload,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'X-License-Key': NR_LICENSE_KEY,
            },
        )
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            if status not in (200, 202):
                print(f"::error::New Relic Log API returned unexpected status {status}")
                print(f"Response: {response.read().decode('utf-8')}")
                sys.exit(1)
            print(f"Log event sent successfully. Response code: {status}")

    except urllib.error.HTTPError as e:
        print(f"::error::HTTP Error: {e.code} - {e.reason}")
        try:
            print(f"Response: {e.read().decode()}")
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"::error::Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

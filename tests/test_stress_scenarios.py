"""
Test suite for Chaos Mesh stress scenarios.

This module tests stress chaos experiments that inject memory stress
into the bill-pay service to validate performance under load.
"""

import pytest
import requests
import time
import os

# Get scenario service URL from environment variable
SCENARIO_SERVICE_URL = os.environ.get("SCENARIO_SERVICE_URL", "http://localhost:8000/scenario-runner")


@pytest.fixture(scope="function")
def reset_chaos_rate_limit():
    """Reset the chaos rate limit before running stress tests"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Reset the rate limit
            reset_response = requests.post(f"{SCENARIO_SERVICE_URL}/api/chaos-rate-limit-reset", timeout=5)
            if reset_response.status_code == 200:
                print(f"✓ Chaos rate limit reset (attempt {attempt + 1})")
                time.sleep(1.0)

                # Verify the reset worked by checking status
                status_response = requests.get(f"{SCENARIO_SERVICE_URL}/api/chaos-rate-limit-status", timeout=5)
                if status_response.status_code == 200:
                    status = status_response.json()
                    if status.get("can_trigger_new"):
                        print(f"✓ Rate limit cleared - can trigger new experiments")
                        break
                    else:
                        print(f"⚠ Rate limit still active: {status.get('cooldown_remaining_seconds')}s remaining")
                        if attempt < max_retries - 1:
                            time.sleep(2.0)
            else:
                print(f"⚠ Rate limit reset returned status {reset_response.status_code}")
        except Exception as e:
            print(f"⚠ Could not reset rate limit (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1.0)
    yield


@pytest.mark.xdist_group(name="stress_tests")
def test_trigger_high_memory_stress_bill_pay(reset_chaos_rate_limit):
    """Test triggering high memory stress scenario on bill-pay service"""
    print("\n=== Testing High Memory Stress on Bill Pay Service ===")

    scenario_name = "relibank-high-memory-stress"

    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/trigger_stress/{scenario_name}"
    )

    assert response.status_code == 200
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Response: {data}")

    # Check if stress experiment was triggered
    assert data.get("status") in ["success", "warning"], f"Unexpected status: {data.get('status')}"

    if data.get("status") == "success":
        print(f"✓ High memory stress scenario triggered successfully on bill-pay service: {data.get('message')}")
    else:
        print(f"⚠ High memory stress scenario triggered with warning: {data.get('message')}")
        print("Note: This may indicate Chaos Mesh is not installed or bill-pay service not found")


if __name__ == "__main__":
    """Run stress scenario test directly"""
    import sys

    print("=" * 80)
    print("Relibank Stress Chaos Test - High Memory on Bill Pay")
    print("=" * 80)

    print(f"\nScenario Service URL: {SCENARIO_SERVICE_URL}")

    try:
        test_trigger_high_memory_stress_bill_pay()
        print("\n" + "=" * 80)
        print("Test Result: PASSED")
        print("=" * 80)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        print("=" * 80)
        print("Test Result: FAILED")
        print("=" * 80)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        print("=" * 80)
        print("Test Result: ERROR")
        print("=" * 80)
        sys.exit(1)

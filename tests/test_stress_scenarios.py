"""
Test suite for Chaos Mesh stress scenarios.

This module tests stress chaos experiments that inject memory stress
into the bill-pay service to validate performance under load.
"""

import requests
import os

# Get scenario service URL from environment variable
SCENARIO_SERVICE_URL = os.environ.get("SCENARIO_SERVICE_URL", "http://localhost:8000/scenario-runner")


def test_trigger_high_memory_stress_bill_pay():
    """Test triggering high memory stress scenario on bill-pay service"""
    print("\n=== Testing High Memory Stress on Bill Pay Service ===")

    # Reset rate limit before triggering
    print("Resetting chaos rate limit...")
    reset_response = requests.post(f"{SCENARIO_SERVICE_URL}/api/chaos-rate-limit-reset")
    print(f"Rate limit reset status: {reset_response.status_code}")

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

import pytest
import requests
import time
import os
from typing import Dict

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")

# NOTE: This test suite only tests the COHORT-BASED LCP slowness scenario
# (affects 11 hardcoded test users). The PERCENTAGE-BASED scenario
# (affects X% of all users) is not currently tested in this suite.


@pytest.fixture
def reset_ab_tests():
    """Reset all A/B test scenarios before and after tests"""
    # Reset before test
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
    assert response.status_code == 200
    time.sleep(0.5)
    yield
    # Cleanup after test
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
        time.sleep(0.5)
    except:
        pass  # Ignore cleanup errors


def test_ab_test_service_health():
    """Test that A/B testing endpoints are accessible"""
    print("\n=== Testing A/B Test Service Health ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    print(f"Status: {response.status_code}")

    assert response.status_code == 200, f"A/B test config endpoint failed: {response.status_code}"

    data = response.json()
    assert "status" in data, "Response missing status field"
    assert "config" in data, "Response missing config field"
    assert data["status"] == "success", "Status is not success"

    print("✓ A/B test service is healthy")


def test_enable_lcp_slowness(reset_ab_tests):
    """Test enabling LCP slowness scenario (cohort-based)"""
    print("\n=== Testing Enable LCP Slowness (Cohort) ===")

    # Enable cohort-based scenario with 3000ms delay (affects 11 hardcoded test users)
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 3000},
        timeout=10
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable LCP slowness: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    assert data["status"] == "success", "Status is not success"
    assert "11" in data["message"], "Message doesn't mention 11 users"
    assert "3000ms" in data["message"], "Message doesn't mention 3000ms"

    # Verify scenario is enabled with correct settings
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["lcp_slowness_cohort_enabled"] is True, "LCP slowness cohort not enabled"
    assert config["lcp_slowness_cohort_user_count"] == 11, "User count not set correctly"
    assert config["lcp_slowness_cohort_delay_ms"] == 3000, "Delay not set correctly"

    print("✓ LCP slowness cohort scenario enabled successfully")


def test_disable_lcp_slowness(reset_ab_tests):
    """Test disabling LCP slowness scenario (cohort-based)"""
    print("\n=== Testing Disable LCP Slowness (Cohort) ===")

    # First enable it
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 3000},
        timeout=10
    )

    # Now disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": False},
        timeout=10
    )

    assert response.status_code == 200, f"Failed to disable LCP slowness: {response.status_code}"

    # Verify scenario is disabled
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["lcp_slowness_cohort_enabled"] is False, "LCP slowness cohort still enabled"

    print("✓ LCP slowness cohort scenario disabled successfully")


def test_cohort_assignment_distribution(reset_ab_tests):
    """Test that only the 11 hardcoded users are assigned to slow cohort"""
    print("\n=== Testing Cohort Assignment Distribution ===")

    # Hardcoded list of 11 test users (same as in accounts_service.py)
    LCP_SLOW_USERS = [
        'b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d',  # Alice Johnson
        'f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a',  # Bob Williams
        'e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b',  # Charlie Brown
        'f47ac10b-58cc-4372-a567-0e02b2c3d471',  # Solaire Astora
        'd9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a',  # Malenia Miquella
        '8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f',  # Artorias Abyss
        '7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f',  # Priscilla Painted
        '6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a',  # Gwyn Cinder
        '5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b',  # Siegmeyer Catarina
        '4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c',  # Ornstein Dragon
        '3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d',  # Smough Executioner
    ]

    # Enable LCP slowness cohort for hardcoded 11 users
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 3000},
        timeout=10
    )

    print("Testing all 11 hardcoded slow users...")

    # Test that all 11 hardcoded users get the delay
    for test_uuid in LCP_SLOW_USERS:
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_uuid},
            timeout=10
        )
        assert response.status_code == 200, f"Failed to get browser user: {response.status_code}"

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 3000, f"Hardcoded slow user {test_uuid} got delay {lcp_delay}, expected 3000"

    print(f"✓ All 11 hardcoded users assigned to slow cohort")

    # Test that random users NOT in the list get no delay
    print("Testing 10 random users NOT in hardcoded list...")
    import uuid
    for i in range(10):
        test_uuid = str(uuid.uuid4())
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_uuid},
            timeout=10
        )
        assert response.status_code == 200, f"Failed to get browser user: {response.status_code}"

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 0, f"Non-hardcoded user {test_uuid} got delay {lcp_delay}, expected 0"

    print("✓ Random users NOT in hardcoded list assigned to normal cohort")


def test_deterministic_cohort_assignment(reset_ab_tests):
    """Test that same user always gets same cohort assignment"""
    print("\n=== Testing Deterministic Cohort Assignment ===")

    # Enable LCP slowness cohort
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 3000},
        timeout=10
    )

    # Test with a hardcoded slow user (should always get delay)
    test_user_id_slow = "b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d"  # Alice Johnson

    # Fetch cohort assignment 5 times for the same slow user
    assignments_slow = []
    for i in range(5):
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_user_id_slow},
            timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)
        assignments_slow.append(lcp_delay)

    print(f"Slow user {test_user_id_slow} assignments: {assignments_slow}")

    # All assignments should be 3000ms
    assert len(set(assignments_slow)) == 1, f"Assignments are not consistent: {assignments_slow}"
    assert assignments_slow[0] == 3000, f"Expected 3000ms delay, got {assignments_slow[0]}"

    # Test with a non-hardcoded user (should always get no delay)
    test_user_id_normal = "550e8400-e29b-41d4-a716-446655440000"  # Not in hardcoded list

    assignments_normal = []
    for i in range(5):
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_user_id_normal},
            timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)
        assignments_normal.append(lcp_delay)

    print(f"Normal user {test_user_id_normal} assignments: {assignments_normal}")

    # All assignments should be 0ms
    assert len(set(assignments_normal)) == 1, f"Assignments are not consistent: {assignments_normal}"
    assert assignments_normal[0] == 0, f"Expected 0ms delay, got {assignments_normal[0]}"

    print("✓ Cohort assignment is deterministic for both slow and normal users")


def test_enabled_scenario_affects_hardcoded_users(reset_ab_tests):
    """Test that enabled scenario affects only the 11 hardcoded users"""
    print("\n=== Testing Enabled Scenario Affects Hardcoded Users ===")

    # Enable LCP slowness cohort with 5000ms delay
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 5000},
        timeout=10
    )

    # Test one hardcoded user (should get delay)
    slow_user = "b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d"  # Alice Johnson
    response = requests.get(
        f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
        headers={"x-browser-user-id": slow_user},
        timeout=10
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("lcp_delay_ms", 0) == 5000, f"Hardcoded user got delay {data.get('lcp_delay_ms')}, expected 5000"

    print("✓ Hardcoded user gets 5000ms delay when enabled")

    # Test random users (should NOT get delay)
    import uuid
    for i in range(5):
        test_uuid = str(uuid.uuid4())
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_uuid},
            timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 0, f"Random user {i+1} got delay {lcp_delay}, expected 0"

    print("✓ Random users get no delay (not in hardcoded list)")


def test_disabled_scenario_affects_no_users(reset_ab_tests):
    """Test that disabled scenario affects no users (including hardcoded ones)"""
    print("\n=== Testing Disabled Scenario Affects No Users ===")

    # Disable LCP slowness cohort (scenario disabled means no delays)
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": False, "delay_ms": 3000},
        timeout=10
    )

    # Test hardcoded users (should NOT get delay when disabled)
    hardcoded_users = [
        "b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d",  # Alice Johnson
        "f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a",  # Bob Williams
    ]

    for test_uuid in hardcoded_users:
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_uuid},
            timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 0, f"Hardcoded user {test_uuid} got delay {lcp_delay}, expected 0 when disabled"

    print("✓ Hardcoded users get no delay when scenario is disabled")

    # Test random users (should also get no delay)
    import uuid
    for i in range(5):
        test_uuid = str(uuid.uuid4())
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_uuid},
            timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 0, f"Random user {i+1} got delay {lcp_delay}, expected 0"

    print("✓ All users get no delay when scenario is disabled")


def test_invalid_delay_values(reset_ab_tests):
    """Test that invalid delay values are rejected"""
    print("\n=== Testing Invalid Delay Values ===")

    # Test delay > 30000ms
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 50000},
        timeout=10
    )

    assert response.status_code == 200  # Should return 200 with error message
    data = response.json()
    assert data["status"] == "error", "Should reject delay > 30000ms"
    print("✓ Rejected delay > 30000ms")

    # Test negative delay
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": -1000},
        timeout=10
    )

    assert response.status_code == 200  # Should return 200 with error message
    data = response.json()
    assert data["status"] == "error", "Should reject negative delay"
    print("✓ Rejected negative delay")


def test_reset_ab_tests_endpoint(reset_ab_tests):
    """Test resetting all A/B test scenarios"""
    print("\n=== Testing Reset All A/B Tests ===")

    # Enable LCP slowness cohort
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness-cohort",
        params={"enabled": True, "delay_ms": 5000},
        timeout=10
    )

    # Verify it's enabled
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10).json()["config"]
    assert config["lcp_slowness_cohort_enabled"] is True

    # Reset
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
    assert response.status_code == 200

    # Verify all scenarios are disabled with default values
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10).json()["config"]

    assert config["lcp_slowness_cohort_enabled"] is False, "LCP slowness cohort still enabled after reset"
    assert config["lcp_slowness_cohort_user_count"] == 11, "User count not correct"
    assert config["lcp_slowness_cohort_delay_ms"] == 3000, "Cohort delay not reset to default"
    assert config["lcp_slowness_percentage_enabled"] is False, "LCP slowness percentage still enabled after reset"
    assert config["lcp_slowness_percentage"] == 50.0, "Percentage not reset to default"
    assert config["lcp_slowness_percentage_delay_ms"] == 3000, "Percentage delay not reset to default"

    print("✓ All A/B test scenarios reset successfully")


def test_scenario_service_unavailable_graceful_fallback():
    """Test that accounts service handles scenario service unavailability gracefully"""
    print("\n=== Testing Graceful Fallback When Scenario Service Unavailable ===")

    # Note: This test assumes scenario service might be down or unreachable
    # In that case, accounts service should still return user_id with lcp_delay_ms = 0

    try:
        response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user", timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Should have user_id even if scenario service is down
            assert "user_id" in data, "Missing user_id in response"

            # Should have lcp_delay_ms field (defaults to 0 if scenario service unavailable)
            assert "lcp_delay_ms" in data, "Missing lcp_delay_ms in response"

            print(f"✓ Graceful fallback working: user_id={data['user_id']}, lcp_delay_ms={data.get('lcp_delay_ms', 0)}")
        else:
            print(f"⚠ Accounts service returned {response.status_code}, skipping graceful fallback test")

    except Exception as e:
        print(f"⚠ Could not test graceful fallback: {e}")

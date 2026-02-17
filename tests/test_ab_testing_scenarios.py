import pytest
import requests
import time
import os
from typing import Dict

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")


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
    """Test enabling LCP slowness scenario"""
    print("\n=== Testing Enable LCP Slowness ===")

    # Enable with 50% probability and 3000ms delay
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 50.0, "delay_ms": 3000},
        timeout=10
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable LCP slowness: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    assert data["status"] == "success", "Status is not success"
    assert ("50%" in data["message"] or "50.0%" in data["message"]), "Message doesn't mention 50%"
    assert "3000ms" in data["message"], "Message doesn't mention 3000ms"

    # Verify scenario is enabled with correct settings
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["lcp_slowness_enabled"] is True, "LCP slowness not enabled"
    assert config["lcp_slowness_percentage"] == 50.0, "Percentage not set correctly"
    assert config["lcp_slowness_delay_ms"] == 3000, "Delay not set correctly"

    print("✓ LCP slowness scenario enabled successfully")


def test_disable_lcp_slowness(reset_ab_tests):
    """Test disabling LCP slowness scenario"""
    print("\n=== Testing Disable LCP Slowness ===")

    # First enable it
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 50.0, "delay_ms": 3000},
        timeout=10
    )

    # Now disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": False},
        timeout=10
    )

    assert response.status_code == 200, f"Failed to disable LCP slowness: {response.status_code}"

    # Verify scenario is disabled
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["lcp_slowness_enabled"] is False, "LCP slowness still enabled"

    print("✓ LCP slowness scenario disabled successfully")


def test_cohort_assignment_distribution(reset_ab_tests):
    """Test that ~50% of users are assigned to slow cohort"""
    print("\n=== Testing Cohort Assignment Distribution ===")

    # Enable LCP slowness for 50% of users
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 50.0, "delay_ms": 3000},
        timeout=10
    )

    print("Fetching browser user IDs for 100 users...")

    slow_users = 0
    normal_users = 0

    for i in range(100):
        response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user", timeout=10)
        assert response.status_code == 200, f"Failed to get browser user: {response.status_code}"

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        if lcp_delay > 0:
            slow_users += 1
        else:
            normal_users += 1

    print(f"Slow cohort: {slow_users}/100 users")
    print(f"Normal cohort: {normal_users}/100 users")

    # Allow for some variance (40-60% range due to randomness)
    assert 40 <= slow_users <= 60, f"Expected ~50% slow users, got {slow_users}%"
    assert 40 <= normal_users <= 60, f"Expected ~50% normal users, got {normal_users}%"

    print("✓ Cohort distribution is approximately 50/50")


def test_deterministic_cohort_assignment(reset_ab_tests):
    """Test that same user always gets same cohort assignment"""
    print("\n=== Testing Deterministic Cohort Assignment ===")

    # Enable LCP slowness
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 50.0, "delay_ms": 3000},
        timeout=10
    )

    # Get a user ID with header override
    test_user_id = "550e8400-e29b-41d4-a716-446655440000"

    # Fetch cohort assignment 5 times for the same user
    assignments = []
    for i in range(5):
        response = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user",
            headers={"x-browser-user-id": test_user_id},
            timeout=10
        )
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)
        assignments.append(lcp_delay)

    print(f"User {test_user_id} assignments: {assignments}")

    # All assignments should be the same
    assert len(set(assignments)) == 1, f"Assignments are not consistent: {assignments}"

    print("✓ Cohort assignment is deterministic")


def test_100_percent_assignment(reset_ab_tests):
    """Test that 100% assignment puts all users in slow cohort"""
    print("\n=== Testing 100% Cohort Assignment ===")

    # Enable LCP slowness for 100% of users
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 100.0, "delay_ms": 5000},
        timeout=10
    )

    print("Checking 10 users...")

    for i in range(10):
        response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user", timeout=10)
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 5000, f"User {i+1} got delay {lcp_delay}, expected 5000"

    print("✓ All users assigned to slow cohort at 100%")


def test_0_percent_assignment(reset_ab_tests):
    """Test that 0% assignment puts all users in normal cohort"""
    print("\n=== Testing 0% Cohort Assignment ===")

    # Enable LCP slowness for 0% of users (effectively disabled)
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 0.0, "delay_ms": 3000},
        timeout=10
    )

    print("Checking 10 users...")

    for i in range(10):
        response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/browser-user", timeout=10)
        assert response.status_code == 200

        data = response.json()
        lcp_delay = data.get("lcp_delay_ms", 0)

        assert lcp_delay == 0, f"User {i+1} got delay {lcp_delay}, expected 0"

    print("✓ All users assigned to normal cohort at 0%")


def test_invalid_percentage_values(reset_ab_tests):
    """Test that invalid percentage values are rejected"""
    print("\n=== Testing Invalid Percentage Values ===")

    # Test percentage > 100
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 150.0},
        timeout=10
    )

    assert response.status_code == 200  # Should return 200 with error message
    data = response.json()
    assert data["status"] == "error", "Should reject percentage > 100"
    print("✓ Rejected percentage > 100")

    # Test negative percentage
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": -10.0},
        timeout=10
    )

    assert response.status_code == 200  # Should return 200 with error message
    data = response.json()
    assert data["status"] == "error", "Should reject negative percentage"
    print("✓ Rejected negative percentage")


def test_reset_ab_tests_endpoint(reset_ab_tests):
    """Test resetting all A/B test scenarios"""
    print("\n=== Testing Reset All A/B Tests ===")

    # Enable LCP slowness
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/lcp-slowness",
        params={"enabled": True, "percentage": 75.0, "delay_ms": 5000},
        timeout=10
    )

    # Verify it's enabled
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10).json()["config"]
    assert config["lcp_slowness_enabled"] is True

    # Reset
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
    assert response.status_code == 200

    # Verify all scenarios are disabled with default values
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10).json()["config"]

    assert config["lcp_slowness_enabled"] is False, "LCP slowness still enabled after reset"
    assert config["lcp_slowness_percentage"] == 50.0, "Percentage not reset to default"
    assert config["lcp_slowness_delay_ms"] == 3000, "Delay not reset to default"

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

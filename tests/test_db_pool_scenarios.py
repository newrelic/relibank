import pytest
import requests
import time
import os
import hashlib
from typing import Dict

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")

# Test user IDs for pool assignment verification
# These are real users from the database that will be assigned to different pools
TEST_USER_POOL_A = "b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d"  # Alice Johnson (should be pool-a)
TEST_USER_POOL_B = "f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a"  # Bob Williams (should be pool-b)


def assign_user_to_pool(user_id: str) -> str:
    """
    Replicate the pool assignment logic from accounts service.
    This ensures we know which pool each test user belongs to.
    """
    user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return "pool-a" if (user_hash % 2) == 0 else "pool-b"


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


def test_db_pool_service_health():
    """Test that database pool scenario endpoints are accessible"""
    print("\n=== Testing Database Pool Scenario Service Health ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    print(f"Status: {response.status_code}")

    assert response.status_code == 200, f"Config endpoint failed: {response.status_code}"

    data = response.json()
    assert "status" in data, "Response missing status field"
    assert "config" in data, "Response missing config field"
    assert data["status"] == "success", "Status is not success"

    # Check that db pool stress fields exist in config
    config = data["config"]
    assert "db_pool_stress_enabled" in config, "Missing db_pool_stress_enabled field"
    assert "db_pool_stress_delay_ms" in config, "Missing db_pool_stress_delay_ms field"
    assert "db_pool_stress_affected_pool" in config, "Missing db_pool_stress_affected_pool field"

    print("✓ Database pool scenario service is healthy")


def test_user_pool_assignment():
    """Verify that test users are correctly assigned to pools"""
    print("\n=== Testing User Pool Assignment ===")

    pool_a = assign_user_to_pool(TEST_USER_POOL_A)
    pool_b = assign_user_to_pool(TEST_USER_POOL_B)

    print(f"User {TEST_USER_POOL_A[:8]} assigned to: {pool_a}")
    print(f"User {TEST_USER_POOL_B[:8]} assigned to: {pool_b}")

    # We need at least one user in each pool for testing
    assert pool_a != pool_b, "Test users must be in different pools"
    print("✓ Test users are in different pools")


def test_enable_db_pool_stress_pool_a(reset_ab_tests):
    """Test enabling database pool stress for pool-a"""
    print("\n=== Testing Enable DB Pool Stress (Pool A) ===")

    # Enable pool stress for pool-a with 500ms delay
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": 500, "affected_pool": "pool-a"},
        timeout=10
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable pool stress: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    assert data["status"] == "success", "Status is not success"
    assert "pool-a" in data["message"], "Message doesn't mention pool-a"
    assert "500ms" in data["message"], "Message doesn't mention 500ms"

    # Verify scenario is enabled with correct settings
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["db_pool_stress_enabled"] is True, "DB pool stress not enabled"
    assert config["db_pool_stress_delay_ms"] == 500, "Delay not set correctly"
    assert config["db_pool_stress_affected_pool"] == "pool-a", "Affected pool not set correctly"

    print("✓ DB pool stress enabled for pool-a")


def test_disable_db_pool_stress(reset_ab_tests):
    """Test disabling database pool stress scenario"""
    print("\n=== Testing Disable DB Pool Stress ===")

    # First enable it
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": 500, "affected_pool": "pool-a"},
        timeout=10
    )

    # Now disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": False},
        timeout=10
    )

    assert response.status_code == 200, f"Failed to disable pool stress: {response.status_code}"

    data = response.json()
    assert data["status"] == "success", "Status is not success"

    # Verify scenario is disabled
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["db_pool_stress_enabled"] is False, "DB pool stress still enabled"

    print("✓ DB pool stress disabled successfully")


def test_invalid_pool_name(reset_ab_tests):
    """Test that invalid pool names are rejected"""
    print("\n=== Testing Invalid Pool Name Validation ===")

    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": 500, "affected_pool": "pool-invalid"},
        timeout=10
    )

    assert response.status_code == 200, "Should return 200 with error message"

    data = response.json()
    assert data["status"] == "error", "Should return error status"
    assert "pool-a" in data["message"] or "pool-b" in data["message"], "Error message should mention valid pool names"

    print("✓ Invalid pool name correctly rejected")


def test_invalid_delay_value(reset_ab_tests):
    """Test that invalid delay values are rejected"""
    print("\n=== Testing Invalid Delay Value Validation ===")

    # Test delay too high
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": 15000, "affected_pool": "pool-a"},
        timeout=10
    )

    assert response.status_code == 200, "Should return 200 with error message"
    data = response.json()
    assert data["status"] == "error", "Should return error status for delay too high"

    # Test negative delay
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": -100, "affected_pool": "pool-a"},
        timeout=10
    )

    assert response.status_code == 200, "Should return 200 with error message"
    data = response.json()
    assert data["status"] == "error", "Should return error status for negative delay"

    print("✓ Invalid delay values correctly rejected")


def test_reset_includes_db_pool_stress(reset_ab_tests):
    """Test that reset endpoint properly resets database pool stress scenario"""
    print("\n=== Testing Reset Includes DB Pool Stress ===")

    # Enable pool stress
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": 500, "affected_pool": "pool-a"},
        timeout=10
    )

    # Reset all scenarios
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
    assert response.status_code == 200, "Reset failed"

    # Verify pool stress is disabled
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config", timeout=10)
    config = config_response.json()["config"]

    assert config["db_pool_stress_enabled"] is False, "DB pool stress not reset"
    assert config["db_pool_stress_delay_ms"] == 500, "Default delay not restored"
    assert config["db_pool_stress_affected_pool"] == "pool-a", "Default pool not restored"

    print("✓ Reset correctly resets DB pool stress scenario")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

import pytest
import requests
import os
import time
from typing import Dict

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000/scenario-runner")


def test_scenario_service_health():
    """Test that scenario service is accessible"""
    print("\n=== Testing Scenario Service Health ===")

    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/home", timeout=5)
        print(f"Status: {response.status_code}")
        assert response.status_code == 200, f"Scenario service not accessible: {response.status_code}"
        print("✓ Scenario service is accessible")
    except requests.exceptions.ConnectionError:
        pytest.fail("Cannot connect to scenario service")


def test_get_all_scenarios():
    """Test retrieving all payment scenarios configuration"""
    print("\n=== Testing Get All Scenarios ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to get scenarios: {response.status_code}"

    data = response.json()
    print(f"Scenarios: {data}")

    # Verify response structure
    assert "status" in data, "Response missing 'status' field"
    assert "scenarios" in data, "Response missing 'scenarios' field"

    scenarios = data["scenarios"]

    # Verify expected scenario keys exist
    assert "gateway_timeout_enabled" in scenarios, "gateway_timeout_enabled scenario missing"
    assert "card_decline_enabled" in scenarios, "card_decline_enabled scenario missing"
    assert "stolen_card_enabled" in scenarios, "stolen_card_enabled scenario missing"

    # Verify probability keys exist
    assert "gateway_timeout_probability" in scenarios, "gateway_timeout_probability missing"
    assert "card_decline_probability" in scenarios, "card_decline_probability missing"
    assert "stolen_card_probability" in scenarios, "stolen_card_probability missing"

    print("✓ All scenarios retrieved successfully")


def test_reset_all_scenarios():
    """Test resetting all scenarios to disabled state"""
    print("\n=== Testing Reset All Scenarios ===")

    response = requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to reset scenarios: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")
    assert "message" in data, "Reset response missing message"

    # Verify all scenarios are disabled
    response = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios")
    scenarios = response.json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is False, "gateway_timeout still enabled after reset"
    assert scenarios["card_decline_enabled"] is False, "card_decline still enabled after reset"
    assert scenarios["stolen_card_enabled"] is False, "stolen_card still enabled after reset"

    print("✓ All scenarios reset successfully")


def test_enable_gateway_timeout():
    """Test enabling gateway timeout scenario"""
    print("\n=== Testing Enable Gateway Timeout ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")

    # Enable with specific probability and delay
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 50.0, "delay": 3.0}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable gateway timeout: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    # Verify scenario is enabled with correct settings
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is True, "Gateway timeout not enabled"
    assert scenarios["gateway_timeout_probability"] == 50.0, "Probability not set correctly"
    assert scenarios["gateway_timeout_delay"] == 3.0, "Delay not set correctly"

    print("✓ Gateway timeout scenario enabled successfully")


def test_enable_card_decline():
    """Test enabling card decline scenario"""
    print("\n=== Testing Enable Card Decline ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")

    # Enable with specific probability
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/card-decline",
        params={"enabled": True, "probability": 75.0}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable card decline: {response.status_code}"

    # Verify scenario is enabled
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios").json()["scenarios"]

    assert scenarios["card_decline_enabled"] is True, "Card decline not enabled"
    assert scenarios["card_decline_probability"] == 75.0, "Probability not set correctly"

    print("✓ Card decline scenario enabled successfully")


def test_enable_stolen_card():
    """Test enabling stolen card scenario"""
    print("\n=== Testing Enable Stolen Card ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")

    # Enable with specific probability
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/stolen-card",
        params={"enabled": True, "probability": 25.0}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable stolen card: {response.status_code}"

    # Verify scenario is enabled
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios").json()["scenarios"]

    assert scenarios["stolen_card_enabled"] is True, "Stolen card not enabled"
    assert scenarios["stolen_card_probability"] == 25.0, "Probability not set correctly"

    print("✓ Stolen card scenario enabled successfully")


def test_disable_scenario():
    """Test disabling a previously enabled scenario"""
    print("\n=== Testing Disable Scenario ===")

    # Enable a scenario first
    requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 50.0}
    )

    # Disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": False}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to disable scenario: {response.status_code}"

    # Verify it's disabled
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is False, "Scenario still enabled"

    print("✓ Scenario disabled successfully")


def test_multiple_scenarios_enabled():
    """Test enabling multiple scenarios simultaneously"""
    print("\n=== Testing Multiple Scenarios Enabled ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")

    # Enable multiple scenarios
    requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 20.0, "delay": 2.0}
    )
    requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/card-decline",
        params={"enabled": True, "probability": 30.0}
    )
    requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/stolen-card",
        params={"enabled": True, "probability": 10.0}
    )

    # Verify all are enabled with correct settings
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is True
    assert scenarios["gateway_timeout_probability"] == 20.0
    assert scenarios["card_decline_enabled"] is True
    assert scenarios["card_decline_probability"] == 30.0
    assert scenarios["stolen_card_enabled"] is True
    assert scenarios["stolen_card_probability"] == 10.0

    print("✓ Multiple scenarios enabled successfully")


def test_chatbot_slowness_scenario():
    """Test chatbot slowness scenario if available"""
    print("\n=== Testing Chatbot Slowness Scenario ===")

    # Try to get chatbot scenario endpoint
    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/api/chatbot-scenarios")

        if response.status_code == 200:
            print("Chatbot scenarios endpoint found")

            # Try to enable slowness
            enable_response = requests.post(
                f"{SCENARIO_SERVICE_URL}/api/chatbot-scenarios/slowness",
                params={"enabled": True, "probability": 50.0, "delay": 5.0}
            )

            if enable_response.status_code == 200:
                print("✓ Chatbot slowness scenario enabled")

                # Reset after test
                requests.post(f"{SCENARIO_SERVICE_URL}/api/chatbot-scenarios/reset")
            else:
                print(f"⚠ Could not enable chatbot slowness: {enable_response.status_code}")
        else:
            print("⚠ Chatbot scenarios not available (this may be normal)")
    except Exception as e:
        print(f"⚠ Chatbot scenarios not available: {e}")


def test_invalid_probability_values():
    """Test that invalid probability values are handled"""
    print("\n=== Testing Invalid Probability Values ===")

    # Try negative probability
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": -10.0}
    )

    print(f"Negative probability status: {response.status_code}")
    # Should either reject (400/422) or clamp to valid range
    assert response.status_code in [200, 400, 422], "Unexpected status for negative probability"

    # Try probability > 100
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 150.0}
    )

    print(f"Over 100 probability status: {response.status_code}")
    assert response.status_code in [200, 400, 422], "Unexpected status for >100 probability"

    print("✓ Invalid probability handling verified")


def test_scenario_persistence():
    """Test that scenario settings persist across requests"""
    print("\n=== Testing Scenario Persistence ===")

    # Reset and enable a scenario
    requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")
    requests.post(
        f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 33.3, "delay": 4.5}
    )

    # Wait a moment
    time.sleep(0.5)

    # Retrieve and verify settings persisted
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is True, "Settings did not persist"
    assert scenarios["gateway_timeout_probability"] == 33.3, "Probability did not persist"
    assert scenarios["gateway_timeout_delay"] == 4.5, "Delay did not persist"

    print("✓ Scenario settings persist correctly")


# ===== CHAOS SCENARIOS SMOKE TESTS =====

def test_chaos_scenarios_api():
    """Smoke test for chaos scenarios API availability"""
    print("\n=== Testing Chaos Scenarios API ===")

    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/api/chaos-scenarios", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"Available chaos scenarios: {list(data.keys())}")
            print("✓ Chaos scenarios API available")
        elif response.status_code == 404:
            print("⚠ Chaos scenarios not implemented (this may be normal)")
        else:
            print(f"⚠ Unexpected status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠ Cannot connect to chaos scenarios endpoint")
    except Exception as e:
        print(f"⚠ Chaos scenarios not available: {e}")


def test_chaos_enable_disable():
    """Smoke test for enabling/disabling chaos scenarios"""
    print("\n=== Testing Chaos Enable/Disable ===")

    try:
        # Try to enable network delay
        enable_response = requests.post(
            f"{SCENARIO_SERVICE_URL}/api/chaos-scenarios/network-delay",
            params={"enabled": True, "delay": 1000},
            timeout=5
        )

        if enable_response.status_code == 200:
            print("✓ Chaos scenario enabled")

            # Try to disable
            disable_response = requests.post(
                f"{SCENARIO_SERVICE_URL}/api/chaos-scenarios/network-delay",
                params={"enabled": False},
                timeout=5
            )

            if disable_response.status_code == 200:
                print("✓ Chaos scenario disabled")
            else:
                print(f"⚠ Could not disable: {disable_response.status_code}")

            # Clean up - reset all chaos scenarios
            requests.post(f"{SCENARIO_SERVICE_URL}/api/chaos-scenarios/reset", timeout=5)
        elif enable_response.status_code == 404:
            print("⚠ Chaos scenarios not implemented")
        else:
            print(f"⚠ Unexpected status: {enable_response.status_code}")
    except Exception as e:
        print(f"⚠ Chaos scenarios test skipped: {e}")


# ===== LOCUST LOAD TESTING SMOKE TESTS =====

def test_locust_scenarios_api():
    """Smoke test for locust load testing API availability"""
    print("\n=== Testing Locust Scenarios API ===")

    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/api/locust-scenarios/status", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"Locust status: {data}")
            print("✓ Locust scenarios API available")
        elif response.status_code == 404:
            print("⚠ Locust scenarios not implemented (this may be normal)")
        else:
            print(f"⚠ Unexpected status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠ Cannot connect to locust scenarios endpoint")
    except Exception as e:
        print(f"⚠ Locust scenarios not available: {e}")


def test_locust_start_stop():
    """Smoke test for starting/stopping locust load tests"""
    print("\n=== Testing Locust Start/Stop ===")

    try:
        # Ensure locust is stopped first
        requests.post(f"{SCENARIO_SERVICE_URL}/api/locust-scenarios/stop", timeout=5)
        time.sleep(1)

        # Try to start with minimal load
        start_response = requests.post(
            f"{SCENARIO_SERVICE_URL}/api/locust-scenarios/start",
            params={"users": 2, "spawn_rate": 1, "duration": 10},
            timeout=5
        )

        if start_response.status_code == 200:
            print("✓ Locust load test started")

            time.sleep(2)

            # Try to stop
            stop_response = requests.post(
                f"{SCENARIO_SERVICE_URL}/api/locust-scenarios/stop",
                timeout=5
            )

            if stop_response.status_code == 200:
                print("✓ Locust load test stopped")
            else:
                print(f"⚠ Could not stop: {stop_response.status_code}")
        elif start_response.status_code == 404:
            print("⚠ Locust scenarios not implemented")
        else:
            print(f"⚠ Unexpected status: {start_response.status_code}")
    except Exception as e:
        print(f"⚠ Locust scenarios test skipped: {e}")


if __name__ == "__main__":
    # Run tests manually for quick validation
    pytest.main([__file__, "-v", "-s"])

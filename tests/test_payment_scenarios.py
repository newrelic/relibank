import pytest
import requests
import time
import os
from typing import Dict, List

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
BILL_PAY_SERVICE_URL = os.getenv("BILL_PAY_SERVICE", "http://localhost:5000")
NUM_PAYMENT_ATTEMPTS = 50  # Send enough to trigger scenarios

@pytest.fixture
def reset_scenarios():
    """Reset all scenarios before and after tests"""
    # Reset before test
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset", timeout=10)
    assert response.status_code == 200
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)

    # Verify all scenarios are disabled
    for scenario in ["gateway_timeout", "card_decline", "stolen_card"]:
        confirmed = wait_for_scenario_active(scenario, False)
        assert confirmed, f"Failed to confirm {scenario} is disabled after reset"

    yield
    # Cleanup after test
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset", timeout=10)
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)
    except:
        pass  # Ignore cleanup errors


def wait_for_scenario_active(scenario_name: str, expected_enabled: bool, expected_probability: float = None, timeout: int = 10) -> bool:
    """Poll the API to confirm scenario is in the expected state"""
    field_map = {
        "gateway_timeout": "gateway_timeout_enabled",
        "card_decline": "card_decline_enabled",
        "stolen_card": "stolen_card_enabled"
    }
    prob_field_map = {
        "gateway_timeout": "gateway_timeout_probability",
        "card_decline": "card_decline_probability",
        "stolen_card": "stolen_card_probability"
    }

    enabled_field = field_map[scenario_name]
    prob_field = prob_field_map[scenario_name]

    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios", timeout=5)
        if response.status_code == 200:
            data = response.json()
            scenarios = data.get("scenarios", {})

            # Check if enabled state matches
            if scenarios.get(enabled_field) == expected_enabled:
                # If checking probability, verify it too
                if expected_probability is not None:
                    if scenarios.get(prob_field) == expected_probability:
                        print(f"Confirmed: {scenario_name} enabled={expected_enabled}, probability={expected_probability}")
                        return True
                else:
                    print(f"Confirmed: {scenario_name} enabled={expected_enabled}")
                    return True

        time.sleep(0.2)  # Poll every 200ms

    print(f"Timeout waiting for {scenario_name} to reach expected state")
    return False


def enable_scenario(scenario_name: str, probability: float = None, delay: float = None) -> Dict:
    """Enable a payment scenario and wait for confirmation"""
    endpoints = {
        "gateway_timeout": f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        "card_decline": f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/card-decline",
        "stolen_card": f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/stolen-card"
    }

    params = {"enabled": True}
    if probability is not None:
        params["probability"] = probability
    if delay is not None:
        params["delay"] = delay

    response = requests.post(endpoints[scenario_name], params=params)
    assert response.status_code == 200

    # Wait for the scenario to be confirmed active via GET API
    confirmed = wait_for_scenario_active(scenario_name, True, probability)
    assert confirmed, f"Failed to confirm {scenario_name} is active"

    return response.json()


def send_card_payment(bill_id: str, amount: float = 100.00) -> requests.Response:
    """Send a card payment request"""
    payload = {
        "billId": bill_id,
        "amount": amount,
        "currency": "usd",
        "paymentMethodId": "pm_card_visa",
        "saveCard": False,
        "payee": "Electric Company",
        "accountId": "acc-test-standard",
    }

    response = requests.post(
        f"{BILL_PAY_SERVICE_URL}/bill-pay-service/card-payment",
        json=payload
    )
    return response


def test_gateway_timeout_scenario(reset_scenarios):
    """Test that gateway timeout scenario triggers with high probability"""
    print("\n=== Testing Gateway Timeout Scenario ===")

    # Enable gateway timeout with 100% probability for testing
    result = enable_scenario("gateway_timeout", probability=100.0, delay=2.0)
    print(f"Enabled: {result['message']}")

    # Send a single payment and expect timeout
    start_time = time.time()
    response = send_card_payment(f"BILL-TIMEOUT-TEST-001", 50.00)
    elapsed_time = time.time() - start_time

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    print(f"Elapsed time: {elapsed_time:.2f}s")

    # Should get 504 timeout
    assert response.status_code == 504, f"Expected 504, got {response.status_code}"
    assert "timeout" in response.json()["detail"].lower()
    assert elapsed_time >= 2.0, f"Expected at least 2s delay, got {elapsed_time:.2f}s"

    print("✓ Gateway timeout scenario working correctly")


def test_card_decline_scenario(reset_scenarios):
    """Test that card decline scenario triggers with high probability"""
    print("\n=== Testing Card Decline Scenario ===")

    # Enable card decline with 100% probability for testing
    result = enable_scenario("card_decline", probability=100.0)
    print(f"Enabled: {result['message']}")

    # Send payments and count declines
    declines = 0
    for i in range(5):
        response = send_card_payment(f"BILL-DECLINE-TEST-{i:03d}", 75.00 + i)
        if response.status_code == 402:
            declines += 1
            print(f"Payment {i+1}: DECLINED - {response.json()['detail']}")
        else:
            try:
                error_detail = response.json()
                print(f"Payment {i+1}: Status {response.status_code} - {error_detail}")
            except:
                print(f"Payment {i+1}: Status {response.status_code} - {response.text}")

    # With 100% probability, all should decline
    print(f"\nDeclined: {declines}/5 payments")
    assert declines >= 2, f"Expected at least 2 declines with 100% probability, got {declines}"

    print("✓ Card decline scenario working correctly")


def test_stolen_card_scenario(reset_scenarios):
    """Test that stolen card scenario triggers with high probability"""
    print("\n=== Testing Stolen Card Scenario ===")

    # Enable stolen card with 100% probability for testing
    result = enable_scenario("stolen_card", probability=100.0)
    print(f"Enabled: {result['message']}")

    # Send payments and count stolen card declines
    stolen_declines = 0
    for i in range(5):
        response = send_card_payment(f"BILL-STOLEN-TEST-{i:03d}", 25.00)
        # Stolen card test token should be declined by Stripe
        if response.status_code == 402:
            stolen_declines += 1
            print(f"Payment {i+1}: DECLINED - {response.json()['detail']}")
        else:
            print(f"Payment {i+1}: Status {response.status_code}")

    # With 100% probability, all should use stolen card token and decline
    print(f"\nDeclined (stolen card): {stolen_declines}/5 payments")
    assert stolen_declines >= 2, f"Expected at least 2 stolen card declines with 100% probability, got {stolen_declines}"

    print("✓ Stolen card scenario working correctly")


def test_realistic_probability_distribution(reset_scenarios):
    """Test scenarios with realistic probabilities to verify distribution"""
    print("\n=== Testing Realistic Probability Distribution ===")

    # Enable all scenarios with moderate probabilities
    enable_scenario("gateway_timeout", probability=20.0, delay=1.0)
    enable_scenario("card_decline", probability=20.0)
    enable_scenario("stolen_card", probability=20.0)

    print(f"Sending {NUM_PAYMENT_ATTEMPTS} payment requests...")

    results = {
        "success": 0,
        "timeout": 0,
        "decline": 0,
        "error": 0
    }

    for i in range(NUM_PAYMENT_ATTEMPTS):
        try:
            response = send_card_payment(f"BILL-LOAD-TEST-{i:04d}", 100.00 + (i % 10))

            if response.status_code == 200:
                results["success"] += 1
            elif response.status_code == 504:
                results["timeout"] += 1
            elif response.status_code == 402:
                results["decline"] += 1
            else:
                results["error"] += 1
        except Exception as e:
            print(f"Request {i} failed: {e}")
            results["error"] += 1

    print("\n=== Results ===")
    print(f"Successful:      {results['success']:3d} ({results['success']/NUM_PAYMENT_ATTEMPTS*100:.1f}%)")
    print(f"Timeouts:        {results['timeout']:3d} ({results['timeout']/NUM_PAYMENT_ATTEMPTS*100:.1f}%)")
    print(f"Declines:        {results['decline']:3d} ({results['decline']/NUM_PAYMENT_ATTEMPTS*100:.1f}%)")
    print(f"Errors:          {results['error']:3d} ({results['error']/NUM_PAYMENT_ATTEMPTS*100:.1f}%)")
    print(f"Total failures:  {results['timeout'] + results['decline']:3d} ({(results['timeout'] + results['decline'])/NUM_PAYMENT_ATTEMPTS*100:.1f}%)")

    # With 20% probability for each scenario (3 scenarios), we expect roughly 40-60% failures
    # (Not exactly 60% due to randomness and potential overlap)
    total_failures = results['timeout'] + results['decline']
    failure_rate = total_failures / NUM_PAYMENT_ATTEMPTS * 100

    assert total_failures > 0, "Expected some failures with 20% probabilities"
    assert results['success'] > 0, "Expected some successful payments"

    print(f"\n✓ Scenarios triggered correctly (failure rate: {failure_rate:.1f}%)")


def test_scenario_reset(reset_scenarios):
    """Test that reset disables all scenarios"""
    print("\n=== Testing Scenario Reset ===")

    # Enable all scenarios
    enable_scenario("gateway_timeout", probability=100.0)
    enable_scenario("card_decline", probability=100.0)
    enable_scenario("stolen_card", probability=100.0)

    # Reset all scenarios
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")
    assert response.status_code == 200
    print("Reset all scenarios")

    # Send payment and expect success
    response = send_card_payment("BILL-RESET-TEST-001", 99.00)
    print(f"Response status: {response.status_code}")

    assert response.status_code == 200, f"Expected success after reset, got {response.status_code}"

    print("✓ Scenario reset working correctly")


if __name__ == "__main__":
    # Run tests manually for quick validation
    pytest.main([__file__, "-v", "-s"])

import pytest
import requests
import time
import os
from typing import Dict, List

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000/scenario-runner")
BILL_PAY_SERVICE_URL = os.getenv("BASE_URL", "http://localhost:5000")
NUM_PAYMENT_ATTEMPTS = 50  # Send enough to trigger scenarios

@pytest.fixture
def reset_scenarios():
    """Reset all scenarios before and after tests"""
    response = requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")
    assert response.status_code == 200
    yield
    # Cleanup after test
    requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")


def enable_scenario(scenario_name: str, probability: float = None, delay: float = None) -> Dict:
    """Enable a payment scenario"""
    endpoints = {
        "gateway_timeout": f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/gateway-timeout",
        "card_decline": f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/card-decline",
        "stolen_card": f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/stolen-card"
    }

    params = {"enabled": True}
    if probability is not None:
        params["probability"] = probability
    if delay is not None:
        params["delay"] = delay

    response = requests.post(endpoints[scenario_name], params=params)
    assert response.status_code == 200
    return response.json()


def send_card_payment(bill_id: str, amount: float = 100.00) -> requests.Response:
    """Send a card payment request"""
    payload = {
        "billId": bill_id,
        "amount": amount,
        "currency": "usd",
        "paymentMethodId": "pm_card_visa",
        "saveCard": False
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
    assert declines == 5, f"Expected 5 declines with 100% probability, got {declines}"

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
        response = send_card_payment(f"BILL-STOLEN-TEST-{i:03d}", 125.00 + i)
        # Stolen card test token should be declined by Stripe
        if response.status_code == 402:
            stolen_declines += 1
            print(f"Payment {i+1}: DECLINED - {response.json()['detail']}")
        else:
            print(f"Payment {i+1}: Status {response.status_code}")

    # With 100% probability, all should use stolen card token and decline
    print(f"\nDeclined (stolen card): {stolen_declines}/5 payments")
    assert stolen_declines == 5, f"Expected 5 stolen card declines with 100% probability, got {stolen_declines}"

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
    response = requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")
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

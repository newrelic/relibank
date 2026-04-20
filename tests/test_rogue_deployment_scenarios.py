import pytest
import requests
import time
import os
from typing import Dict

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
SUPPORT_SERVICE_URL = os.getenv("SUPPORT_SERVICE", "http://localhost:5003")
NUM_RISK_ASSESSMENTS = 20  # Number of risk assessments to test

@pytest.fixture
def reset_risk_scenarios():
    """Reset all risk assessment scenarios before and after tests"""
    # Reset before test
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)
    assert response.status_code == 200

    # Verify rogue agent is disabled
    confirmed = wait_for_agent_config("gpt-4o", False)
    assert confirmed, "Failed to confirm rogue agent is disabled after reset"

    yield
    # Cleanup after test
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)
    except:
        pass  # Ignore cleanup errors


def wait_for_agent_config(expected_agent: str, expected_rogue_enabled: bool, timeout: int = 10) -> bool:
    """Poll the API to confirm agent configuration is in the expected state"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/config", timeout=5)
        if response.status_code == 200:
            data = response.json()
            scenarios = data.get("scenarios", {})

            agent_name = scenarios.get("agent_name")
            rogue_enabled = scenarios.get("rogue_agent_enabled")

            if agent_name == expected_agent and rogue_enabled == expected_rogue_enabled:
                print(f"Confirmed: agent={expected_agent}, rogue_enabled={expected_rogue_enabled}")
                return True

        time.sleep(0.2)  # Poll every 200ms

    print(f"Timeout waiting for agent config to reach expected state")
    return False


def enable_rogue_agent() -> Dict:
    """Enable rogue agent and wait for confirmation"""
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/rogue-agent",
        params={"enabled": True},
        timeout=10
    )
    assert response.status_code == 200
    result = response.json()

    # Wait for confirmation
    confirmed = wait_for_agent_config("gpt-4o-mini", True)
    assert confirmed, "Failed to confirm rogue agent is enabled"

    return result


def disable_rogue_agent() -> Dict:
    """Disable rogue agent and wait for confirmation"""
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/rogue-agent",
        params={"enabled": False},
        timeout=10
    )
    assert response.status_code == 200
    result = response.json()

    # Wait for confirmation
    confirmed = wait_for_agent_config("gpt-4o", False)
    assert confirmed, "Failed to confirm rogue agent is disabled"

    return result


def assess_payment_risk(transaction_data: Dict) -> Dict:
    """Call Support Service to assess payment risk"""
    response = requests.post(
        f"{SUPPORT_SERVICE_URL}/support-service/assess-payment-risk",
        json=transaction_data,
        timeout=30
    )
    if response.status_code != 200:
        print(f"Error response: {response.status_code}")
        print(f"Response body: {response.text}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    return response.json()


def test_get_risk_assessment_config(reset_risk_scenarios):
    """Test getting current risk assessment configuration"""
    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/config", timeout=10)
    assert response.status_code == 200

    data = response.json()
    assert "scenarios" in data
    scenarios = data["scenarios"]

    assert "rogue_agent_enabled" in scenarios
    assert "agent_name" in scenarios
    assert scenarios["agent_name"] in ["gpt-4o", "gpt-4o-mini"]

    # After reset, should be using gpt-4o
    assert scenarios["agent_name"] == "gpt-4o"
    assert scenarios["rogue_agent_enabled"] is False


def test_enable_rogue_agent(reset_risk_scenarios):
    """Test enabling rogue agent switches to gpt-4o-mini"""
    result = enable_rogue_agent()

    assert result["status"] == "success"
    assert "gpt-4o-mini" in result["message"]
    assert result["scenarios"]["rogue_agent_enabled"] is True
    assert result["scenarios"]["agent_name"] == "gpt-4o-mini"

    print("✓ Rogue agent enabled successfully")


def test_disable_rogue_agent(reset_risk_scenarios):
    """Test disabling rogue agent switches back to gpt-4o"""
    # First enable
    enable_rogue_agent()

    # Then disable
    result = disable_rogue_agent()

    assert result["status"] == "success"
    assert "gpt-4o" in result["message"]
    assert result["scenarios"]["rogue_agent_enabled"] is False
    assert result["scenarios"]["agent_name"] == "gpt-4o"

    print("✓ Rogue agent disabled successfully")


def test_normal_agent_approves_legitimate_payments(reset_risk_scenarios):
    """Test that normal agent (gpt-4o) approves legitimate low-risk payments"""
    # Ensure using normal agent
    disable_rogue_agent()

    # Test with low-risk transaction
    transaction = {
        "transaction_id": "txn_test_normal_001",
        "account_id": "acc_test_123",
        "amount": 25.00,
        "payee": "Amazon",
        "payment_method": "checking"
    }

    result = assess_payment_risk(transaction)

    assert "risk_level" in result
    assert "risk_score" in result
    assert "decision" in result
    assert "reason" in result
    assert "agent_model" in result

    # Normal agent should approve low-risk payments
    assert result["decision"] == "approved"
    assert result["agent_model"] == "gpt-4o (gpt-4o)"

    print(f"✓ Normal agent approved payment: risk_level={result['risk_level']}, risk_score={result['risk_score']}")


def test_rogue_agent_declines_most_payments(reset_risk_scenarios):
    """Test that rogue agent (gpt-4o-mini) declines most payments"""
    # Enable rogue agent
    enable_rogue_agent()

    # Test with same transaction that normal agent would approve
    transaction = {
        "transaction_id": "txn_test_rogue_001",
        "account_id": "acc_test_123",
        "amount": 75.00,  # Over $50, should be declined by rogue agent
        "payee": "Unknown Vendor",
        "payment_method": "checking"
    }

    result = assess_payment_risk(transaction)

    assert "risk_level" in result
    assert "risk_score" in result
    assert "decision" in result
    assert "reason" in result
    assert "agent_model" in result

    # Rogue agent should decline this payment
    assert result["decision"] == "declined"
    assert result["agent_model"] == "gpt-4o-mini (gpt-4o-mini)"
    assert result["risk_level"] in ["medium", "high"]

    print(f"✓ Rogue agent declined payment: risk_level={result['risk_level']}, risk_score={result['risk_score']}")


def test_rogue_agent_high_decline_rate(reset_risk_scenarios):
    """Test that rogue agent has significantly higher decline rate than normal agent"""
    # Test with normal agent first
    disable_rogue_agent()

    normal_declined = 0
    for i in range(NUM_RISK_ASSESSMENTS):
        transaction = {
            "transaction_id": f"txn_normal_{i}",
            "account_id": "acc_test_123",
            "amount": 50.0 + (i * 10),  # Varying amounts
            "payee": f"Vendor {i}",
            "payment_method": "checking"
        }

        result = assess_payment_risk(transaction)
        if result["decision"] == "declined":
            normal_declined += 1

        time.sleep(0.5)  # Small delay between requests

    normal_decline_rate = (normal_declined / NUM_RISK_ASSESSMENTS) * 100

    # Now test with rogue agent
    enable_rogue_agent()

    rogue_declined = 0
    for i in range(NUM_RISK_ASSESSMENTS):
        transaction = {
            "transaction_id": f"txn_rogue_{i}",
            "account_id": "acc_test_123",
            "amount": 50.0 + (i * 10),  # Same varying amounts
            "payee": f"Vendor {i}",
            "payment_method": "checking"
        }

        result = assess_payment_risk(transaction)
        if result["decision"] == "declined":
            rogue_declined += 1

        time.sleep(0.5)  # Small delay between requests

    rogue_decline_rate = (rogue_declined / NUM_RISK_ASSESSMENTS) * 100

    print(f"Normal agent decline rate: {normal_decline_rate:.1f}% ({normal_declined}/{NUM_RISK_ASSESSMENTS})")
    print(f"Rogue agent decline rate: {rogue_decline_rate:.1f}% ({rogue_declined}/{NUM_RISK_ASSESSMENTS})")

    # Rogue agent should have MUCH higher decline rate (at least 3x higher)
    assert rogue_decline_rate > normal_decline_rate * 3, \
        f"Rogue agent decline rate ({rogue_decline_rate:.1f}%) not significantly higher than normal ({normal_decline_rate:.1f}%)"

    # Rogue agent should decline at least 60% of payments
    assert rogue_decline_rate >= 60, \
        f"Rogue agent decline rate ({rogue_decline_rate:.1f}%) should be at least 60%"

    print(f"✓ Rogue agent has significantly higher decline rate ({rogue_decline_rate:.1f}% vs {normal_decline_rate:.1f}%)")


def test_reset_risk_scenarios(reset_risk_scenarios):
    """Test resetting risk scenarios returns to defaults"""
    # Enable rogue agent
    enable_rogue_agent()

    # Verify it's enabled
    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/config", timeout=10)
    data = response.json()
    assert data["scenarios"]["rogue_agent_enabled"] is True

    # Reset
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "success"
    assert "reset" in result["message"].lower()

    # Verify defaults
    confirmed = wait_for_agent_config("gpt-4o", False)
    assert confirmed

    print("✓ Risk assessment scenarios reset successfully")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

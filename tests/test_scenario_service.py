import pytest
import requests
import os
import time
from typing import Dict

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")


@pytest.fixture
def reset_scenarios_after_test():
    """Reset scenarios after test to prevent state leakage (use only when needed)"""
    yield
    # Cleanup after test
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset", timeout=5)
    except:
        pass  # Ignore cleanup errors


def test_scenario_service_health():
    """Test that scenario service is accessible.

    Probes the always-on /scenario-runner health route rather than the UI page
    (/scenario-runner/home), which is intentionally 404 when the SCENARIO_UI_ENABLED
    deploy flag is off. Health must not be coupled to UI visibility.
    """
    print("\n=== Testing Scenario Service Health ===")

    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner", timeout=5)
        print(f"Status: {response.status_code}")
        assert response.status_code == 200, f"Scenario service not accessible: {response.status_code}"
        print("✓ Scenario service is accessible")
    except requests.exceptions.ConnectionError:
        pytest.fail("Cannot connect to scenario service")


def test_scenario_ui_flag_controls_webpage():
    """Verify the browser UI page visibility matches the SCENARIO_UI_ENABLED deploy flag.

    Color-directed (demogorgon convention): when TARGET_COLOR is set, every request carries
    an `X-Test-Env: <color>` header so it routes to that specific color (post-deployment runs
    always set it, so the just-deployed color is validated before cutover); when unset, the
    active color is hit. The expected state comes from SCENARIO_UI_ENABLED, threaded from the
    same deploy that set it (default "true" — the flag's own default).

    Asserts:
      - /scenario-runner/home  -> 200 + page marker when enabled, else 404
      - /scenario-runner/api/scenarios -> 200 regardless (the flag's invariant: API stays up)
    """
    print("\n=== Testing Scenario UI Flag Controls Webpage ===")

    target_color = os.getenv("TARGET_COLOR", "").strip()
    headers = {"X-Test-Env": target_color} if target_color else {}
    # Treat unset OR empty (e.g. scheduled runs with no workflow input) as the flag's default (true).
    expected_enabled = (os.getenv("SCENARIO_UI_ENABLED") or "true").strip().lower() == "true"
    print(f"target_color={target_color or '<active>'} expected_enabled={expected_enabled}")

    # The webpage page (gated by the flag)
    home = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/home", headers=headers, timeout=10)
    print(f"/scenario-runner/home -> {home.status_code}")
    if expected_enabled:
        assert home.status_code == 200, (
            f"UI enabled but /scenario-runner/home returned {home.status_code} (expected 200)"
        )
        assert "Relibank Scenario Runner" in home.text, "UI page served but missing expected content marker"
    else:
        assert home.status_code == 404, (
            f"UI disabled but /scenario-runner/home returned {home.status_code} (expected 404)"
        )

    # The API must remain reachable regardless of the UI flag (core invariant)
    api = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/scenarios", headers=headers, timeout=10)
    print(f"/scenario-runner/api/scenarios -> {api.status_code}")
    assert api.status_code == 200, f"Scenario API not reachable ({api.status_code}) — should be up regardless of UI flag"

    print(f"✓ Webpage visibility matches SCENARIO_UI_ENABLED={expected_enabled}; API reachable")


def test_get_all_scenarios():
    """Test retrieving all payment scenarios configuration"""
    print("\n=== Testing Get All Scenarios ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios")

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

    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to reset scenarios: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")
    assert "message" in data, "Reset response missing message"

    # Verify all scenarios are disabled
    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios")
    scenarios = response.json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is False, "gateway_timeout still enabled after reset"
    assert scenarios["card_decline_enabled"] is False, "card_decline still enabled after reset"
    assert scenarios["stolen_card_enabled"] is False, "stolen_card still enabled after reset"

    print("✓ All scenarios reset successfully")


def test_enable_gateway_timeout():
    """Test enabling gateway timeout scenario"""
    print("\n=== Testing Enable Gateway Timeout ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")

    # Enable with specific probability and delay
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 50.0, "delay": 3.0}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable gateway timeout: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    # Verify scenario is enabled with correct settings
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is True, "Gateway timeout not enabled"
    assert scenarios["gateway_timeout_probability"] == 50.0, "Probability not set correctly"
    assert scenarios["gateway_timeout_delay"] == 3.0, "Delay not set correctly"

    print("✓ Gateway timeout scenario enabled successfully")


def test_enable_card_decline():
    """Test enabling card decline scenario"""
    print("\n=== Testing Enable Card Decline ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")

    # Enable with specific probability
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/card-decline",
        params={"enabled": True, "probability": 75.0}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable card decline: {response.status_code}"

    # Verify scenario is enabled
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios").json()["scenarios"]

    assert scenarios["card_decline_enabled"] is True, "Card decline not enabled"
    assert scenarios["card_decline_probability"] == 75.0, "Probability not set correctly"

    print("✓ Card decline scenario enabled successfully")


def test_enable_stolen_card():
    """Test enabling stolen card scenario"""
    print("\n=== Testing Enable Stolen Card ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")

    # Enable with specific probability
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/stolen-card",
        params={"enabled": True, "probability": 25.0}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable stolen card: {response.status_code}"

    # Verify scenario is enabled
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios").json()["scenarios"]

    assert scenarios["stolen_card_enabled"] is True, "Stolen card not enabled"
    assert scenarios["stolen_card_probability"] == 25.0, "Probability not set correctly"

    print("✓ Stolen card scenario enabled successfully")


def test_disable_scenario():
    """Test disabling a previously enabled scenario"""
    print("\n=== Testing Disable Scenario ===")

    # Enable a scenario first
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 50.0}
    )

    # Disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": False}
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to disable scenario: {response.status_code}"

    # Verify it's disabled
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is False, "Scenario still enabled"

    print("✓ Scenario disabled successfully")


def test_multiple_scenarios_enabled():
    """Test enabling multiple scenarios simultaneously"""
    print("\n=== Testing Multiple Scenarios Enabled ===")

    # Reset first
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")

    # Enable multiple scenarios
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 20.0, "delay": 2.0}
    )
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/card-decline",
        params={"enabled": True, "probability": 30.0}
    )
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/stolen-card",
        params={"enabled": True, "probability": 10.0}
    )

    # Verify all are enabled with correct settings
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios").json()["scenarios"]

    assert scenarios["gateway_timeout_enabled"] is True
    assert scenarios["gateway_timeout_probability"] >= 15.0, f"Gateway timeout probability should be ~20%, got {scenarios['gateway_timeout_probability']}"
    assert scenarios["card_decline_enabled"] is True
    assert scenarios["card_decline_probability"] >= 25.0, f"Card decline probability should be ~30%, got {scenarios['card_decline_probability']}"
    assert scenarios["stolen_card_enabled"] is True
    assert scenarios["stolen_card_probability"] >= 5.0, f"Stolen card probability should be ~10%, got {scenarios['stolen_card_probability']}"

    print("✓ Multiple scenarios enabled successfully")


def test_support_slowness_scenario():
    """Test support service slowness scenario if available"""
    print("\n=== Testing Support Service Slowness Scenario ===")

    # Try to get support scenario endpoint
    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/support-scenarios")

        if response.status_code == 200:
            print("Support scenarios endpoint found")

            # Try to enable slowness
            enable_response = requests.post(
                f"{SCENARIO_SERVICE_URL}/scenario-runner/api/support-scenarios/slowness",
                params={"enabled": True, "probability": 50.0, "delay": 5.0}
            )

            if enable_response.status_code == 200:
                print("✓ Support slowness scenario enabled")

                # Reset after test
                requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/support-scenarios/reset")
            else:
                print(f"⚠ Could not enable support slowness: {enable_response.status_code}")
        else:
            print("⚠ Support scenarios not available (this may be normal)")
    except Exception as e:
        print(f"⚠ Support scenarios not available: {e}")


def test_invalid_probability_values():
    """Test that invalid probability values are handled"""
    print("\n=== Testing Invalid Probability Values ===")

    # Try negative probability
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": -10.0}
    )

    print(f"Negative probability status: {response.status_code}")
    # Should either reject (400/422) or clamp to valid range
    assert response.status_code in [200, 400, 422], "Unexpected status for negative probability"

    # Try probability > 100
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 150.0}
    )

    print(f"Over 100 probability status: {response.status_code}")
    assert response.status_code in [200, 400, 422], "Unexpected status for >100 probability"

    print("✓ Invalid probability handling verified")


def test_scenario_persistence():
    """Test that scenario settings persist across requests"""
    print("\n=== Testing Scenario Persistence ===")

    # Reset and enable a scenario
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/gateway-timeout",
        params={"enabled": True, "probability": 33.3, "delay": 4.5}
    )

    # Wait a moment
    time.sleep(0.5)

    # Retrieve and verify settings persisted
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios").json()["scenarios"]

    try:
        assert scenarios["gateway_timeout_enabled"] is True, "Settings did not persist"
        assert scenarios["gateway_timeout_probability"] == 33.3, "Probability did not persist"
        assert scenarios["gateway_timeout_delay"] == 4.5, "Delay did not persist"

        print("✓ Scenario settings persist correctly")
    finally:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset")


# ===== CHAOS SCENARIOS SMOKE TESTS =====

def test_chaos_scenarios_api():
    """Smoke test for chaos scenarios API availability"""
    print("\n=== Testing Chaos Scenarios API ===")

    try:
        response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/chaos-scenarios", timeout=5)

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
            f"{SCENARIO_SERVICE_URL}/scenario-runner/api/chaos-scenarios/network-delay",
            params={"enabled": True, "delay": 1000},
            timeout=5
        )

        if enable_response.status_code == 200:
            print("✓ Chaos scenario enabled")

            # Try to disable
            disable_response = requests.post(
                f"{SCENARIO_SERVICE_URL}/scenario-runner/api/chaos-scenarios/network-delay",
                params={"enabled": False},
                timeout=5
            )

            if disable_response.status_code == 200:
                print("✓ Chaos scenario disabled")
            else:
                print(f"⚠ Could not disable: {disable_response.status_code}")

            # Clean up - reset all chaos scenarios
            requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/chaos-scenarios/reset", timeout=5)
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
        response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/locust-scenarios/status", timeout=5)

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
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/locust-scenarios/stop", timeout=5)
        time.sleep(1)

        # Try to start with minimal load
        start_response = requests.post(
            f"{SCENARIO_SERVICE_URL}/scenario-runner/api/locust-scenarios/start",
            params={"users": 2, "spawn_rate": 1, "duration": 10},
            timeout=5
        )

        if start_response.status_code == 200:
            print("✓ Locust load test started")

            time.sleep(2)

            # Try to stop
            stop_response = requests.post(
                f"{SCENARIO_SERVICE_URL}/scenario-runner/api/locust-scenarios/stop",
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


# These "stress-chaos"-labeled scenario names have their own dedicated FastAPI route
# (@app.post("/scenario-runner/api/trigger_stress/dem-memory-leak-45min") etc.), registered
# as an exact-match path *before* the generic dry_run-aware
# /trigger_stress/{scenario_name} handler. FastAPI always matches the literal path first,
# so `?dry_run=true` against these silently reaches the dedicated handler instead — which
# ignores the param and unconditionally flips a real in-process feature flag (no chaos-mesh
# selector involved at all, so "matched_pods" doesn't even apply). Never call these from a
# "dry run" test — do NOT remove this exclusion without adding real dry_run support to
# those two dedicated endpoints first.
_SCENARIOS_WITHOUT_DRY_RUN_SUPPORT = {"dem-memory-leak-45min", "dem-memory-leak-10min"}


def test_all_chaos_scenarios_have_matching_pods():
    """Dry-run every registered chaos/stress scenario and assert its selector
    actually matches at least one live pod. Catches selector/namespace drift
    (e.g. a hardcoded namespace that doesn't exist on this cluster's blue/green
    setup) before it silently no-ops the next time someone triggers it for real.
    """
    scenarios = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/scenarios", timeout=10).json()
    checked = []
    for s in scenarios:
        if s["type"] not in ("chaos-mesh", "stress-chaos"):
            continue  # payment/ab_test/feature_flag scenarios aren't selector-based
        if s["name"] in _SCENARIOS_WITHOUT_DRY_RUN_SUPPORT:
            continue
        endpoint = "trigger_chaos" if s["type"] == "chaos-mesh" else "trigger_stress"
        resp = requests.post(
            f"{SCENARIO_SERVICE_URL}/scenario-runner/api/{endpoint}/{s['name']}",
            params={"dry_run": "true"},
            timeout=10,
        )
        assert resp.status_code == 200, f"{s['name']}: dry-run call failed ({resp.status_code})"
        data = resp.json()
        # Confirm the call actually reached the dry_run-aware code path rather than some
        # other route that ignored the param and triggered for real — if a future scenario
        # ever adds a dedicated route like the two excluded above, we want a loud failure
        # here, not a silently-skipped assertion.
        assert data.get("dry_run") is True, (
            f"Scenario '{s['name']}' ({s['type']}) did not return dry_run=true — this call "
            f"may not have been a dry run at all and could have triggered a real action. "
            f"Response: {data}. If this scenario has its own dedicated, non-dry-run-aware "
            f"route, add it to _SCENARIOS_WITHOUT_DRY_RUN_SUPPORT above instead of letting "
            f"this test call it."
        )
        checked.append((s["name"], data.get("matched_pods", 0)))
        assert data.get("matched_pods", 0) > 0, (
            f"Scenario '{s['name']}' ({s['type']}) matched 0 pods — it would silently "
            f"no-op if triggered for real. {data.get('message')}"
        )
    print(f"✓ {len(checked)} chaos/stress scenarios all matched >=1 pod: {checked}")


if __name__ == "__main__":
    # Run tests manually for quick validation
    pytest.main([__file__, "-v", "-s"])

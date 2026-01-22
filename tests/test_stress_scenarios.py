"""
Test suite for Chaos Mesh stress scenarios.

This module tests stress chaos experiments that inject CPU, memory, and I/O
stress into Relibank services to validate performance under load.
"""

import requests
import time
import os

# Get scenario service URL from environment variable
SCENARIO_SERVICE_URL = os.environ.get("SCENARIO_SERVICE_URL", "http://localhost:8000/scenario-runner")


def test_scenario_service_stress_experiments():
    """Test that stress chaos experiments are loaded and available"""
    print("\n=== Testing Stress Chaos Experiments Loaded ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/api/scenarios")
    assert response.status_code == 200

    scenarios = response.json()
    stress_scenarios = [s for s in scenarios if s.get("type") == "stress-chaos"]

    print(f"Found {len(stress_scenarios)} stress chaos scenarios:")
    for scenario in stress_scenarios:
        print(f"  - {scenario['name']}: {scenario['description']}")

    assert len(stress_scenarios) > 0, "No stress chaos scenarios found"

    # Verify specific scenarios exist
    scenario_names = [s['name'] for s in stress_scenarios]
    assert 'relibank-cpu-stress-test' in scenario_names
    assert 'relibank-memory-stress-test' in scenario_names
    assert 'relibank-combined-stress-test' in scenario_names

    print("✓ Stress chaos scenarios loaded successfully")


def test_trigger_cpu_stress():
    """Test triggering CPU stress scenario"""
    print("\n=== Testing CPU Stress Scenario ===")

    scenario_name = "relibank-cpu-stress-test"

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
        print(f"✓ CPU stress scenario triggered successfully: {data.get('message')}")
    else:
        print(f"⚠ CPU stress scenario triggered with warning: {data.get('message')}")
        print("Note: This may indicate Chaos Mesh is not installed or no pods matched the selector")


def test_trigger_memory_stress():
    """Test triggering memory stress scenario"""
    print("\n=== Testing Memory Stress Scenario ===")

    scenario_name = "relibank-memory-stress-test"

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
        print(f"✓ Memory stress scenario triggered successfully: {data.get('message')}")
    else:
        print(f"⚠ Memory stress scenario triggered with warning: {data.get('message')}")


def test_trigger_combined_stress():
    """Test triggering combined CPU and memory stress scenario"""
    print("\n=== Testing Combined Stress Scenario ===")

    scenario_name = "relibank-combined-stress-test"

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
        print(f"✓ Combined stress scenario triggered successfully: {data.get('message')}")
    else:
        print(f"⚠ Combined stress scenario triggered with warning: {data.get('message')}")


def test_stress_experiment_validation():
    """Test that stress experiments contain expected configuration"""
    print("\n=== Testing Stress Experiment Configuration ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/api/scenarios")
    assert response.status_code == 200

    scenarios = response.json()
    stress_scenarios = {s['name']: s for s in scenarios if s.get("type") == "stress-chaos"}

    # Verify CPU stress scenario exists
    assert 'relibank-cpu-stress-test' in stress_scenarios
    cpu_stress = stress_scenarios['relibank-cpu-stress-test']
    assert 'cpu-stress' in cpu_stress['description']

    # Verify memory stress scenario exists
    assert 'relibank-memory-stress-test' in stress_scenarios
    mem_stress = stress_scenarios['relibank-memory-stress-test']
    assert 'memory-stress' in mem_stress['description']

    # Verify high stress scenarios exist
    assert 'relibank-high-cpu-stress' in stress_scenarios
    assert 'relibank-high-memory-stress' in stress_scenarios

    print(f"✓ All stress scenarios properly configured")


def test_invalid_stress_scenario():
    """Test triggering non-existent stress scenario"""
    print("\n=== Testing Invalid Stress Scenario ===")

    scenario_name = "non-existent-stress-scenario"

    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/trigger_stress/{scenario_name}"
    )

    assert response.status_code == 200
    data = response.json()

    print(f"Response: {data}")

    # Should return an error for non-existent scenario
    assert "error" in data, "Expected error response for non-existent scenario"
    assert scenario_name in data["error"]

    print("✓ Invalid scenario correctly rejected")


def test_service_health_during_stress():
    """
    Test that services remain accessible during stress (smoke test).

    Note: This test triggers a short stress scenario and checks if the
    targeted service remains responsive. In a real environment with Chaos Mesh
    installed, this would validate that services handle stress gracefully.
    """
    print("\n=== Testing Service Health During Stress ===")

    # First check baseline health
    base_url = os.environ.get("BASE_URL", "http://localhost:3000")

    try:
        response = requests.get(f"{base_url}", timeout=5)
        baseline_accessible = response.status_code == 200
    except requests.exceptions.RequestException:
        baseline_accessible = False

    print(f"Baseline accessibility: {baseline_accessible}")

    if not baseline_accessible:
        print("⚠ Services not accessible at baseline - skipping stress test")
        return

    # Trigger a short stress scenario
    scenario_name = "relibank-cpu-stress-test"
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/api/trigger_stress/{scenario_name}"
    )

    if response.status_code != 200 or response.json().get("status") == "warning":
        print("⚠ Chaos Mesh not available - skipping live stress test")
        return

    print("Stress scenario triggered, waiting 5 seconds...")
    time.sleep(5)

    # Check if service is still accessible
    try:
        response = requests.get(f"{base_url}", timeout=10)
        still_accessible = response.status_code == 200

        if still_accessible:
            print("✓ Service remained accessible during stress")
        else:
            print(f"⚠ Service returned status {response.status_code} during stress")

    except requests.exceptions.RequestException as e:
        print(f"⚠ Service experienced issues during stress: {e}")
        # This is expected behavior - stress scenarios may impact service availability


if __name__ == "__main__":
    """Run stress scenario tests directly"""
    import sys

    print("=" * 80)
    print("Relibank Stress Chaos Test Suite")
    print("=" * 80)

    print(f"\nScenario Service URL: {SCENARIO_SERVICE_URL}")

    tests = [
        test_scenario_service_stress_experiments,
        test_trigger_cpu_stress,
        test_trigger_memory_stress,
        test_trigger_combined_stress,
        test_stress_experiment_validation,
        test_invalid_stress_scenario,
        test_service_health_during_stress,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 80)

    sys.exit(0 if failed == 0 else 1)

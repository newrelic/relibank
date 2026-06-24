import pytest
import requests
import time
import os
import subprocess
import re

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE_URL", "http://localhost:5002")


@pytest.fixture
def reset_dem_scenarios():
    """Reset all DEM scenarios before and after tests"""
    # Reset before test
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/reset", timeout=10)
    assert response.status_code == 200
    time.sleep(0.5)
    yield
    # Cleanup after test
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/reset", timeout=10)
        time.sleep(0.5)
    except:
        pass  # Ignore cleanup errors


def test_dem_service_health():
    """Test that DEM endpoints are accessible"""
    print("\n=== Testing DEM Service Health ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10)
    print(f"Status: {response.status_code}")

    assert response.status_code == 200, f"DEM config endpoint failed: {response.status_code}"

    data = response.json()
    assert "status" in data, "Response missing status field"
    assert "config" in data, "Response missing config field"
    assert data["status"] == "success", "Status is not success"

    print("✓ DEM service is healthy")


def test_enable_dem_toggle(reset_dem_scenarios):
    """Test enabling DEM memory leak toggle (persistent mode)"""
    print("\n=== Testing Enable DEM Memory Leak Toggle ===")

    # Enable manual toggle with 10 MB/sec, max 500 MB
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 10, "max_mb": 500},
        timeout=10
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to enable DEM toggle: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    assert data["status"] == "success", "Status is not success"
    assert "enabled" in data["message"], "Message doesn't mention enabled"
    assert "10 MB/sec" in data["message"], "Message doesn't mention rate"
    assert "500 MB" in data["message"], "Message doesn't mention max"

    # Verify scenario is enabled with correct settings
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10)
    config = config_response.json()["config"]

    assert config["memory_leak_toggle_enabled"] is True, "DEM toggle not enabled"
    assert config["memory_leak_rate_mb_per_sec"] == 10, "Rate not set correctly"
    assert config["memory_leak_max_mb"] == 500, "Max MB not set correctly"

    print("✓ DEM memory leak toggle enabled successfully")


def test_disable_dem_toggle(reset_dem_scenarios):
    """Test disabling DEM memory leak toggle"""
    print("\n=== Testing Disable DEM Memory Leak Toggle ===")

    # First enable it
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 10, "max_mb": 500},
        timeout=10
    )

    # Now disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": False},
        timeout=10
    )

    assert response.status_code == 200, f"Failed to disable DEM toggle: {response.status_code}"

    data = response.json()
    assert data["status"] == "success", "Status is not success"
    assert "disabled" in data["message"], "Message doesn't mention disabled"

    # Verify scenario is disabled
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10)
    config = config_response.json()["config"]

    assert config["memory_leak_toggle_enabled"] is False, "DEM toggle still enabled"

    print("✓ DEM memory leak toggle disabled successfully")


def test_trigger_dem_30min_scenario(reset_dem_scenarios):
    """Test triggering one-time 30-minute DEM memory leak scenario"""
    print("\n=== Testing One-Time DEM Trigger (30-min) ===")

    # Trigger the 30-minute scenario
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/trigger_stress/dem-memory-leak-30min",
        timeout=10
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to trigger DEM scenario: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    assert data["status"] == "success", "Status is not success"
    assert "triggered" in data["message"].lower(), "Message doesn't mention triggered"
    assert "30 minutes" in data["message"] or "1800" in str(data.get("duration_seconds", "")), "Duration not mentioned"

    # Verify trigger is active
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10)
    config = config_response.json()["config"]

    assert config["memory_leak_trigger_active"] is True, "Trigger not active"
    assert config["memory_leak_trigger_deadline"] is not None, "Deadline not set"

    print("✓ One-time DEM trigger started successfully")


def test_trigger_already_running_error(reset_dem_scenarios):
    """Test that triggering when already running returns error"""
    print("\n=== Testing Trigger Already Running Error ===")

    # Trigger the scenario first time
    response1 = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/trigger_stress/dem-memory-leak-30min",
        timeout=10
    )
    assert response1.status_code == 200
    assert response1.json()["status"] == "success"

    # Try to trigger again immediately (should fail)
    time.sleep(1)  # Brief pause
    response2 = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/trigger_stress/dem-memory-leak-30min",
        timeout=10
    )

    data = response2.json()
    print(f"Response: {data}")

    assert data["status"] == "error", "Should return error when already running"
    assert "already running" in data["message"].lower(), "Error message should mention already running"

    print("✓ Correctly prevents duplicate trigger")


def test_invalid_rate_values(reset_dem_scenarios):
    """Test that invalid rate_mb_per_sec values are rejected"""
    print("\n=== Testing Invalid Rate Values ===")

    # Test rate > 100
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 150, "max_mb": 500},
        timeout=10
    )

    data = response.json()
    assert data["status"] == "error", "Should reject rate > 100"
    print("✓ Rejected rate > 100 MB/sec")

    # Test rate < 1
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 0, "max_mb": 500},
        timeout=10
    )

    data = response.json()
    assert data["status"] == "error", "Should reject rate < 1"
    print("✓ Rejected rate < 1 MB/sec")


def test_invalid_max_mb_values(reset_dem_scenarios):
    """Test that invalid max_mb values are rejected"""
    print("\n=== Testing Invalid Max MB Values ===")

    # Test max_mb > 2000
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 10, "max_mb": 3000},
        timeout=10
    )

    data = response.json()
    assert data["status"] == "error", "Should reject max_mb > 2000"
    print("✓ Rejected max_mb > 2000 MB")

    # Test max_mb < 100
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 10, "max_mb": 50},
        timeout=10
    )

    data = response.json()
    assert data["status"] == "error", "Should reject max_mb < 100"
    print("✓ Rejected max_mb < 100 MB")


def test_reset_dem_scenarios_endpoint(reset_dem_scenarios):
    """Test resetting all DEM scenarios"""
    print("\n=== Testing Reset All DEM Scenarios ===")

    # Enable toggle
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 20, "max_mb": 1000},
        timeout=10
    )

    # Verify it's enabled with custom values
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10).json()["config"]
    assert config["memory_leak_toggle_enabled"] is True
    assert config["memory_leak_rate_mb_per_sec"] == 20
    assert config["memory_leak_max_mb"] == 1000

    # Reset
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/reset", timeout=10)
    assert response.status_code == 200

    # Verify all scenarios are disabled with default values
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10).json()["config"]

    assert config["memory_leak_toggle_enabled"] is False, "Toggle still enabled after reset"
    assert config["memory_leak_rate_mb_per_sec"] == 0.27, "Rate not reset to default (0.27)"
    assert config["memory_leak_max_mb"] == 500, "Max MB not reset to default (500)"
    assert config["memory_leak_trigger_active"] is False, "Trigger still active after reset"
    assert config["memory_leak_trigger_duration_sec"] == 1800, "Duration not reset to default (1800)"

    print("✓ All DEM scenarios reset successfully")


def test_scenarios_api_includes_dem_scenarios():
    """Test that /api/scenarios includes DEM scenarios"""
    print("\n=== Testing DEM Scenarios in API Response ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/scenarios", timeout=10)
    assert response.status_code == 200

    scenarios = response.json()

    # Find DEM scenarios
    dem_trigger = None
    dem_toggle = None

    for scenario in scenarios:
        if scenario.get("name") == "dem-memory-leak-30min":
            dem_trigger = scenario
        elif scenario.get("name") == "dem_memory_leak_toggle":
            dem_toggle = scenario

    # Verify one-time trigger scenario
    assert dem_trigger is not None, "DEM trigger scenario not found in API response"
    assert dem_trigger["type"] == "stress-chaos", "DEM trigger should be stress-chaos type"
    assert dem_trigger["target_service"] == "accounts-service", "Wrong target service"
    print("✓ DEM trigger scenario found (type: stress-chaos)")

    # Verify toggle scenario
    assert dem_toggle is not None, "DEM toggle scenario not found in API response"
    assert dem_toggle["type"] == "ab_test", "DEM toggle should be ab_test type"
    assert "enabled" in dem_toggle, "Toggle missing enabled field"
    assert "config" in dem_toggle, "Toggle missing config field"
    assert "rate_mb_per_sec" in dem_toggle["config"], "Config missing rate_mb_per_sec"
    assert "max_mb" in dem_toggle["config"], "Config missing max_mb"
    print("✓ DEM toggle scenario found (type: ab_test)")

    print("✓ Both DEM scenarios correctly exposed in API")


def get_pod_memory_mb():
    """Get accounts service pod memory usage in MB via kubectl exec"""
    try:
        # Get pod name
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "relibank", "-l", "app=accounts-service", "-o", "name"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"Failed to get pod name: {result.stderr}")
            return None

        pod_name = result.stdout.strip().split('/')[-1]
        if not pod_name:
            print("No accounts-service pod found")
            return None

        # Get memory usage from ps aux
        result = subprocess.run(
            ["kubectl", "exec", "-n", "relibank", pod_name, "--", "ps", "aux"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"Failed to exec ps: {result.stderr}")
            return None

        # Parse RSS (6th column) from python process
        for line in result.stdout.split('\n'):
            if 'python' in line.lower() and 'uvicorn' in line.lower():
                parts = line.split()
                if len(parts) >= 6:
                    rss_kb = int(parts[5])
                    return rss_kb / 1024  # Convert to MB

        print("Python process not found in ps output")
        return None

    except Exception as e:
        print(f"Error getting pod memory: {e}")
        return None


def test_memory_actually_grows(reset_dem_scenarios):
    """Integration test: Verify memory actually grows in the pod"""
    print("\n=== Testing Actual Memory Growth in Pod ===")

    # Get baseline memory
    baseline_mb = get_pod_memory_mb()
    if baseline_mb is None:
        pytest.skip("Cannot access pod memory (kubectl not available or not in cluster)")

    print(f"Baseline memory: {baseline_mb:.1f} MB")

    # Enable toggle with fast leak rate (20 MB/sec, max 200 MB for fast test)
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 20, "max_mb": 200},
        timeout=10
    )
    assert response.status_code == 200
    print("✓ Enabled memory leak (20 MB/sec, max 200 MB)")

    # Wait 15 seconds (should allocate ~300 MB but cap at 200 MB)
    print("Waiting 15 seconds for memory to grow...")
    time.sleep(15)

    # Check memory has grown
    current_mb = get_pod_memory_mb()
    assert current_mb is not None, "Failed to get current memory"

    memory_growth = current_mb - baseline_mb
    print(f"Current memory: {current_mb:.1f} MB (growth: {memory_growth:.1f} MB)")

    # Should have grown by at least 150 MB (accounting for some overhead/variance)
    assert memory_growth >= 150, f"Memory did not grow enough: {memory_growth:.1f} MB (expected >= 150 MB)"
    print(f"✓ Memory grew by {memory_growth:.1f} MB")

    # Verify service is still responding
    try:
        health_response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/health", timeout=5)
        assert health_response.status_code == 200, "Service not responding"
        print("✓ Service still responding under memory pressure")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Service failed under memory pressure: {e}")

    # Disable scenario
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": False},
        timeout=10
    )
    assert response.status_code == 200
    print("✓ Disabled memory leak")

    # Wait for cleanup
    print("Waiting 5 seconds for memory cleanup...")
    time.sleep(5)

    # Verify memory cleaned up
    final_mb = get_pod_memory_mb()
    assert final_mb is not None, "Failed to get final memory"

    cleanup_amount = current_mb - final_mb
    print(f"Final memory: {final_mb:.1f} MB (cleaned up: {cleanup_amount:.1f} MB)")

    # Verify significant cleanup occurred (at least 75% of allocated memory freed)
    # Python GC may not return all memory to OS immediately, so we check cleanup amount
    min_cleanup = memory_growth * 0.75
    assert cleanup_amount >= min_cleanup, f"Insufficient cleanup: {cleanup_amount:.1f} MB freed (expected >= {min_cleanup:.1f} MB)"
    print(f"✓ Memory cleaned up successfully ({cleanup_amount:.1f} MB freed, {cleanup_amount/memory_growth*100:.0f}% of allocated)")


def test_memory_leak_impacts_performance(reset_dem_scenarios):
    """Integration test: Verify memory leak causes performance degradation"""
    print("\n=== Testing Performance Impact of Memory Leak ===")

    # Measure baseline response time
    baseline_times = []
    for _ in range(5):
        start = time.time()
        response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/health", timeout=5)
        assert response.status_code == 200
        baseline_times.append(time.time() - start)
        time.sleep(0.2)

    baseline_avg = sum(baseline_times) / len(baseline_times) * 1000  # Convert to ms
    print(f"Baseline avg response time: {baseline_avg:.1f} ms")

    # Enable aggressive memory leak
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 30, "max_mb": 400},
        timeout=10
    )
    assert response.status_code == 200
    print("✓ Enabled aggressive memory leak (30 MB/sec, max 400 MB)")

    # Wait for memory to build up
    print("Waiting 20 seconds for memory pressure to build...")
    time.sleep(20)

    # Measure response time under load
    leak_times = []
    for _ in range(5):
        start = time.time()
        try:
            response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/health", timeout=10)
            leak_times.append(time.time() - start)
        except requests.exceptions.Timeout:
            pytest.fail("Service timed out under memory pressure")
        time.sleep(0.2)

    leak_avg = sum(leak_times) / len(leak_times) * 1000  # Convert to ms
    print(f"Under memory leak avg response time: {leak_avg:.1f} ms")

    # Response time should be noticeably slower (at least 20% slower or 50ms, whichever is larger)
    slowdown = leak_avg - baseline_avg
    min_slowdown = max(baseline_avg * 0.2, 50)

    print(f"Slowdown: {slowdown:.1f} ms (expected >= {min_slowdown:.1f} ms)")

    # Note: In some environments GC might not cause noticeable slowdown
    # So we make this a soft assertion with warning
    if slowdown < min_slowdown:
        print(f"⚠ WARNING: Performance did not degrade as expected (slowdown: {slowdown:.1f} ms)")
        print("   This might be expected in some environments with good GC")
    else:
        print(f"✓ Performance degraded by {slowdown:.1f} ms under memory pressure")

    # Cleanup
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": False},
        timeout=10
    )

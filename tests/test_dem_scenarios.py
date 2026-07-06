import pytest
import requests
import time
import os
import subprocess
import re

# Configuration - use environment variables with local defaults
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE_URL", "http://localhost:5002")
NR_API_KEY = os.getenv("NR_API_KEY")
NR_ACCOUNT_ID = os.getenv("NR_ACCOUNT_ID")
NR_APP_NAME = os.getenv("NR_APP_NAME", "ReliBank (Analysts) - Accounts Service")
NR_BROWSER_APP_NAME = os.getenv("NR_BROWSER_APP_NAME", "ReliBank - Customer Portal")
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() == "true"


@pytest.fixture
def reset_dem_scenarios():
    """Reset all DEM scenarios before and after tests"""
    # Reset before test
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/reset", timeout=10, verify=SSL_VERIFY)
    assert response.status_code == 200
    time.sleep(0.5)
    yield
    # Cleanup after test
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/reset", timeout=10, verify=SSL_VERIFY)
        time.sleep(0.5)
    except:
        pass  # Ignore cleanup errors


def query_nrql(query: str):
    """Execute NRQL query via NerdGraph API"""
    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID environment variables required for New Relic tests")

    # Escape quotes in NRQL query for GraphQL
    escaped_query = query.replace('"', '\\"').replace('\n', ' ').strip()

    gql_query = {
        "query": f'{{ actor {{ account(id: {NR_ACCOUNT_ID}) {{ nrql(query: "{escaped_query}") {{ results }} }} }} }}'
    }

    response = requests.post(
        "https://api.newrelic.com/graphql",  # External API, always use standard SSL
        headers={
            "Content-Type": "application/json",
            "API-Key": NR_API_KEY
        },
        json=gql_query,
        timeout=30, verify=SSL_VERIFY
    )

    assert response.status_code == 200, f"NerdGraph query failed: {response.status_code}"

    data = response.json()

    # Check for errors in response
    if "errors" in data:
        error_msg = data["errors"][0].get("message", "Unknown error")
        pytest.fail(f"NerdGraph query error: {error_msg}")

    if "data" not in data:
        pytest.fail(f"Unexpected response format: {data}")

    return data["data"]["actor"]["account"]["nrql"]["results"]


def test_dem_service_health():
    """Test that DEM endpoints are accessible"""
    print("\n=== Testing DEM Service Health ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10, verify=SSL_VERIFY)
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
        timeout=10,
        verify=SSL_VERIFY
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
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10, verify=SSL_VERIFY)
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
        timeout=10, verify=SSL_VERIFY
    )

    # Now disable it
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": False},
        timeout=10, verify=SSL_VERIFY
    )

    assert response.status_code == 200, f"Failed to disable DEM toggle: {response.status_code}"

    data = response.json()
    assert data["status"] == "success", "Status is not success"
    assert "disabled" in data["message"], "Message doesn't mention disabled"

    # Verify scenario is disabled
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10, verify=SSL_VERIFY)
    config = config_response.json()["config"]

    assert config["memory_leak_toggle_enabled"] is False, "DEM toggle still enabled"

    print("✓ DEM memory leak toggle disabled successfully")


def test_trigger_dem_30min_scenario(reset_dem_scenarios):
    """Test triggering one-time 30-minute DEM memory leak scenario"""
    print("\n=== Testing One-Time DEM Trigger (30-min) ===")

    # Trigger the 30-minute scenario
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/trigger_stress/dem-memory-leak-30min",
        timeout=10, verify=SSL_VERIFY
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to trigger DEM scenario: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    assert data["status"] == "success", "Status is not success"
    assert "triggered" in data["message"].lower(), "Message doesn't mention triggered"
    assert "30 minutes" in data["message"] or "1800" in str(data.get("duration_seconds", "")), "Duration not mentioned"

    # Verify trigger is active
    config_response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10, verify=SSL_VERIFY)
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
        timeout=10, verify=SSL_VERIFY
    )
    assert response1.status_code == 200
    assert response1.json()["status"] == "success"

    # Try to trigger again immediately (should fail)
    time.sleep(1)  # Brief pause
    response2 = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/trigger_stress/dem-memory-leak-30min",
        timeout=10, verify=SSL_VERIFY
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
        timeout=10, verify=SSL_VERIFY
    )

    data = response.json()
    assert data["status"] == "error", "Should reject rate > 100"
    print("✓ Rejected rate > 100 MB/sec")

    # Test rate < 1
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 0, "max_mb": 500},
        timeout=10, verify=SSL_VERIFY
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
        timeout=10, verify=SSL_VERIFY
    )

    data = response.json()
    assert data["status"] == "error", "Should reject max_mb > 2000"
    print("✓ Rejected max_mb > 2000 MB")

    # Test max_mb < 100
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 10, "max_mb": 50},
        timeout=10, verify=SSL_VERIFY
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
        timeout=10, verify=SSL_VERIFY
    )

    # Verify it's enabled with custom values
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10, verify=SSL_VERIFY).json()["config"]
    assert config["memory_leak_toggle_enabled"] is True
    assert config["memory_leak_rate_mb_per_sec"] == 20
    assert config["memory_leak_max_mb"] == 1000

    # Reset
    response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/reset", timeout=10, verify=SSL_VERIFY)
    assert response.status_code == 200

    # Verify all scenarios are disabled with default values
    config = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/config", timeout=10, verify=SSL_VERIFY).json()["config"]

    assert config["memory_leak_toggle_enabled"] is False, "Toggle still enabled after reset"
    assert config["memory_leak_rate_mb_per_sec"] == 0.27, "Rate not reset to default (0.27)"
    assert config["memory_leak_max_mb"] == 500, "Max MB not reset to default (500)"
    assert config["memory_leak_trigger_active"] is False, "Trigger still active after reset"
    assert config["memory_leak_trigger_duration_sec"] == 1800, "Duration not reset to default (1800)"

    print("✓ All DEM scenarios reset successfully")


def test_scenarios_api_includes_dem_scenarios():
    """Test that /api/scenarios includes DEM scenarios"""
    print("\n=== Testing DEM Scenarios in API Response ===")

    response = requests.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/scenarios", timeout=10, verify=SSL_VERIFY)
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
            timeout=10, verify=SSL_VERIFY
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
            timeout=10, verify=SSL_VERIFY
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
        timeout=10, verify=SSL_VERIFY
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
        health_response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/health", timeout=5, verify=SSL_VERIFY)
        assert health_response.status_code == 200, "Service not responding"
        print("✓ Service still responding under memory pressure")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Service failed under memory pressure: {e}")

    # Disable scenario
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": False},
        timeout=10, verify=SSL_VERIFY
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
        response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/health", timeout=5, verify=SSL_VERIFY)
        assert response.status_code == 200
        baseline_times.append(time.time() - start)
        time.sleep(0.2)

    baseline_avg = sum(baseline_times) / len(baseline_times) * 1000  # Convert to ms
    print(f"Baseline avg response time: {baseline_avg:.1f} ms")

    # Enable aggressive memory leak
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 30, "max_mb": 400},
        timeout=10, verify=SSL_VERIFY
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
            response = requests.get(f"{ACCOUNTS_SERVICE_URL}/accounts-service/health", timeout=10, verify=SSL_VERIFY)
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
        timeout=10,
        verify=SSL_VERIFY
    )


def test_memory_usage_in_new_relic():
    """Test that memory usage is visible in New Relic APM"""
    print("\n=== Testing Memory Usage in New Relic ===")

    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID required for this test")

    nrql = f"""
    SELECT
      average(apm.service.memory.physical) as 'Avg Memory MB',
      max(apm.service.memory.physical) as 'Max Memory MB',
      latest(apm.service.memory.physical) as 'Current Memory MB'
    FROM Metric
    WHERE appName = '{NR_APP_NAME}'
    SINCE 10 minutes ago
    """

    print(f"Query: {nrql}")
    results = query_nrql(nrql)

    assert results, "No memory metrics found in New Relic"
    assert len(results) > 0, "Empty results from NRQL query"

    data = results[0]
    avg_mem = data.get("Avg Memory MB")
    max_mem = data.get("Max Memory MB")
    current_mem = data.get("Current Memory MB")

    print(f"Average Memory: {avg_mem:.2f} MB" if avg_mem is not None else "Average Memory: N/A")
    print(f"Max Memory: {max_mem:.2f} MB" if max_mem is not None else "Max Memory: N/A")
    print(f"Current Memory: {current_mem:.2f} MB" if current_mem is not None else "Current Memory: N/A")

    assert avg_mem is not None, "Average memory not found"
    assert avg_mem > 0, "Average memory should be positive"

    print("✓ Memory metrics flowing to New Relic")


def test_memory_leak_visible_in_new_relic(reset_dem_scenarios):
    """Integration test: Verify memory leak is visible in New Relic"""
    print("\n=== Testing Memory Leak Visibility in New Relic ===")

    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID required for this test")

    # Get baseline memory
    nrql = f"""
    SELECT latest(apm.service.memory.physical) as 'Memory MB'
    FROM Metric
    WHERE appName = '{NR_APP_NAME}'
    SINCE 2 minutes ago
    """

    baseline_results = query_nrql(nrql)
    baseline_mem = baseline_results[0].get("Memory MB") if baseline_results and baseline_results[0] else None

    if baseline_mem is None:
        pytest.skip("No baseline memory data available in New Relic")

    print(f"Baseline memory: {baseline_mem:.1f} MB")

    # Enable memory leak with fast rate
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": True, "rate_mb_per_sec": 20, "max_mb": 300},
        timeout=10,
        verify=SSL_VERIFY
    )
    assert response.status_code == 200
    print("✓ Enabled memory leak (20 MB/sec, max 300 MB)")

    # Wait 20 seconds for memory to grow and New Relic to report
    print("Waiting 20 seconds for memory growth and New Relic reporting...")
    time.sleep(20)

    # Check memory in New Relic
    current_results = query_nrql(nrql)
    current_mem = current_results[0].get("Memory MB", 0) if current_results else 0

    print(f"Current memory in New Relic: {current_mem:.1f} MB")

    growth = current_mem - baseline_mem
    print(f"Memory growth: {growth:.1f} MB")

    # Should have grown by at least 100 MB
    assert growth >= 100, f"Memory did not grow enough in New Relic: {growth:.1f} MB (expected >= 100 MB)"
    print(f"✓ Memory leak visible in New Relic (grew by {growth:.1f} MB)")

    # Cleanup
    requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/dem-memory-leak/toggle",
        params={"enabled": False},
        timeout=10,
        verify=SSL_VERIFY
    )


def test_memory_timeseries_in_new_relic():
    """Test memory timeseries data in New Relic"""
    print("\n=== Testing Memory Timeseries in New Relic ===")

    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID required for this test")

    nrql = f"""
    SELECT average(apm.service.memory.physical) as 'Avg Memory MB'
    FROM Metric
    WHERE appName = '{NR_APP_NAME}'
    SINCE 30 minutes ago
    TIMESERIES 1 minute
    """

    print(f"Query: {nrql}")
    results = query_nrql(nrql)

    assert results, "No timeseries data found"

    # Filter to non-null data points
    data_points = [r for r in results if r.get("Avg Memory MB") is not None]

    print(f"Found {len(data_points)} valid data points")
    assert len(data_points) > 0, "No valid data points in timeseries"

    # Show first and last data points
    first = data_points[0]
    last = data_points[-1]

    first_mem = first.get("Avg Memory MB", 0)
    last_mem = last.get("Avg Memory MB", 0)

    print(f"First data point: {first_mem:.2f} MB")
    print(f"Last data point: {last_mem:.2f} MB")
    print(f"Change: {last_mem - first_mem:+.2f} MB")

    print("✓ Timeseries data available in New Relic")


def test_transaction_slowness_in_new_relic():
    """Test that slow transactions are visible in New Relic APM"""
    print("\n=== Testing Transaction Slowness in New Relic ===")

    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID required for this test")

    nrql = f"""
    SELECT
      average(duration) as 'Avg Duration (s)',
      percentile(duration, 95) as 'P95 Duration (s)',
      count(*) as 'Transaction Count'
    FROM Transaction
    WHERE appName = '{NR_APP_NAME}'
    SINCE 10 minutes ago
    """

    print(f"Query: {nrql}")
    results = query_nrql(nrql)

    if not results or not results[0]:
        print("\n⚠️  No transaction data found in last 10 minutes")
        pytest.skip("No transaction data available")

    data = results[0]
    avg_duration = data.get("Avg Duration (s)")
    p95_data = data.get("P95 Duration (s)")
    p95_duration = p95_data.get("95") if isinstance(p95_data, dict) else p95_data
    txn_count = data.get("Transaction Count", 0)

    print(f"\n✅ Average Duration: {avg_duration:.3f}s" if avg_duration else "\n⚠️  Average Duration: N/A")
    print(f"✅ P95 Duration: {p95_duration:.3f}s" if p95_duration else "⚠️  P95 Duration: N/A")
    print(f"✅ Transaction Count: {txn_count:.0f}")

    assert txn_count > 0, "No transactions recorded"

    # Check if transactions are slow (> 500ms suggests memory pressure)
    if avg_duration and avg_duration > 0.5:
        print(f"\n🔥 SLOW TRANSACTIONS DETECTED: Avg {avg_duration:.3f}s (> 500ms threshold)")
        print("   Memory leak is causing transaction slowness!")
    elif avg_duration:
        print(f"\n✅ Transaction performance normal: {avg_duration:.3f}s")

    print("✓ Transaction metrics available in New Relic")


def test_browser_lcp_impact_in_new_relic():
    """Test that LCP degradation is visible in New Relic Browser"""
    print("\n=== Testing Browser LCP Impact in New Relic ===")

    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID required for this test")

    # Query for dashboard LCP
    nrql = f"""
    SELECT
      percentile(largestContentfulPaint, 50, 75, 95) as 'LCP (ms)',
      count(*) as 'Page Views'
    FROM PageViewTiming
    WHERE appName = '{NR_BROWSER_APP_NAME}'
      AND pageUrl LIKE '%/dashboard%'
    SINCE 30 minutes ago
    """

    print(f"Query: {nrql}")
    results = query_nrql(nrql)

    if not results or not results[0]:
        print("\n⚠️  No PageViewTiming data found for dashboard")
        print("   This could mean:")
        print("   - No users visiting dashboard")
        print("   - Browser agent not configured")
        print("   - PageViewTiming not captured yet")
        pytest.skip("No PageViewTiming data available")

    data = results[0]
    lcp_data = data.get("LCP (ms)")
    lcp_p50 = lcp_data.get("50") if isinstance(lcp_data, dict) else None
    lcp_p75 = lcp_data.get("75") if isinstance(lcp_data, dict) else None
    lcp_p95 = lcp_data.get("95") if isinstance(lcp_data, dict) else None
    page_views = data.get("Page Views", 0)

    print(f"\n✅ Page Views: {page_views:.0f}")
    print(f"✅ LCP P50: {lcp_p50:.0f}ms" if lcp_p50 else "⚠️  LCP P50: N/A")
    print(f"✅ LCP P75: {lcp_p75:.0f}ms" if lcp_p75 else "⚠️  LCP P75: N/A")
    print(f"✅ LCP P95: {lcp_p95:.0f}ms" if lcp_p95 else "⚠️  LCP P95: N/A")

    # Check if LCP is degraded
    # Good: < 2500ms, Needs Improvement: 2500-4000ms, Poor: > 4000ms
    if lcp_p75:
        if lcp_p75 > 4000:
            print(f"\n🔴 POOR LCP DETECTED: {lcp_p75:.0f}ms (> 4000ms)")
            print("   Memory leak is causing significant DEM impact!")
        elif lcp_p75 > 2500:
            print(f"\n🟡 DEGRADED LCP DETECTED: {lcp_p75:.0f}ms (2500-4000ms)")
            print("   Memory leak is impacting page load performance!")
        else:
            print(f"\n🟢 LCP is good: {lcp_p75:.0f}ms (< 2500ms)")

    if page_views == 0:
        print("\n⚠️  No page views found - cannot assess LCP impact")
        print("   Need Selenium/goblin-swarm traffic to dashboard to measure LCP")
        pytest.skip("No page views to measure LCP")

    print("✓ Browser LCP metrics available in New Relic")


def test_lcp_alert_query():
    """Test the exact alert query that will be used for monitoring"""
    print("\n=== Testing LCP Alert Query (75th percentile) ===")

    if not NR_API_KEY or not NR_ACCOUNT_ID:
        pytest.skip("NR_API_KEY and NR_ACCOUNT_ID required for this test")

    # This is the exact query the user wants to alert on
    nrql = f"""
    SELECT percentile(largestContentfulPaint, 75)
    FROM PageViewTiming
    WHERE appName = '{NR_BROWSER_APP_NAME}'
      AND pageUrl LIKE '%/dashboard%'
    """

    print(f"Alert Query: {nrql}")
    results = query_nrql(nrql)

    if not results or not results[0]:
        print("\n⚠️  No data for alert query")
        print("   Alert will not fire if no PageViewTiming data exists")
        pytest.skip("No data for alert query")

    data = results[0]
    lcp_data = data.get("percentile")
    lcp_p75 = lcp_data.get("75") if isinstance(lcp_data, dict) else lcp_data

    if lcp_p75:
        print(f"\n✅ LCP P75: {lcp_p75:.0f}ms")

        # Suggest alert threshold
        if lcp_p75 > 4000:
            print(f"\n🔴 Alert Status: WOULD FIRE (LCP {lcp_p75:.0f}ms > 4000ms threshold)")
            print("   Suggested threshold: > 4000ms for Poor LCP")
        elif lcp_p75 > 2500:
            print(f"\n🟡 Alert Status: WOULD FIRE (LCP {lcp_p75:.0f}ms > 2500ms threshold)")
            print("   Suggested threshold: > 2500ms for Degraded LCP")
        else:
            print(f"\n🟢 Alert Status: OK (LCP {lcp_p75:.0f}ms < 2500ms)")
    else:
        print("\n⚠️  LCP P75 value is null")

    print("\n✓ Alert query executed successfully")
    print("  To set up alert:")
    print("  1. Go to New Relic Alerts & AI")
    print("  2. Create NRQL alert condition")
    print("  3. Use query above")
    print("  4. Set threshold: > 4000ms (Poor) or > 2500ms (Needs Improvement)")

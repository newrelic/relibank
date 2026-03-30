#!/usr/bin/env python3
"""
End-to-end test for database pool performance scenario.
Enables the scenario, sends traffic, and validates custom attributes in New Relic.
"""
import pytest
import requests
import time
import os
import hashlib

# Configuration
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")
NR_USER_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NR_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")
NERDGRAPH_URL = "https://api.newrelic.com/graphql"

# Test users
TEST_USER_POOL_A = "b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d"  # Alice Johnson
TEST_USER_POOL_B = "f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a"  # Bob Williams

# Skip test if New Relic credentials not provided
pytestmark = pytest.mark.skipif(
    not NR_USER_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set"
)


def query_nerdgraph(nrql_query):
    """Execute a NRQL query via NerdGraph API"""
    graphql_query = """
    query($accountId: Int!, $nrql: Nrql!) {
      actor {
        account(id: $accountId) {
          nrql(query: $nrql) {
            results
          }
        }
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "API-Key": NR_USER_API_KEY
    }

    variables = {
        "accountId": int(NR_ACCOUNT_ID),
        "nrql": nrql_query
    }

    payload = {
        "query": graphql_query,
        "variables": variables
    }

    response = requests.post(NERDGRAPH_URL, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        return None

    data = response.json()

    if "errors" in data:
        return None

    return data.get("data", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])


@pytest.fixture
def reset_scenario():
    """Reset scenario before and after test"""
    # Reset before
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
    time.sleep(0.5)
    yield
    # Reset after
    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/reset", timeout=10)
        time.sleep(0.5)
    except:
        pass


def test_db_pool_e2e_with_new_relic_validation(reset_scenario):
    """
    End-to-end test: Enable scenario, generate traffic, validate in New Relic
    """
    print("\n" + "=" * 70)
    print("Database Pool Performance E2E Test")
    print("=" * 70)

    # Step 1: Enable the scenario
    print("\n📝 Step 1: Enabling database pool stress scenario...")
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/db-pool-stress",
        params={"enabled": True, "delay_ms": 500, "affected_pool": "pool-a"},
        timeout=10
    )
    assert response.status_code == 200, f"Failed to enable scenario: {response.status_code}"

    config = response.json()
    assert config["status"] == "success"
    assert config["config"]["db_pool_stress_enabled"] is True
    print("✅ Scenario enabled successfully")

    # Step 2: Verify scenario is enabled
    print("\n📝 Step 2: Verifying scenario configuration...")
    config_response = requests.get(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/ab-testing/config",
        timeout=10
    )
    assert config_response.status_code == 200
    config_data = config_response.json()["config"]
    assert config_data["db_pool_stress_enabled"] is True
    assert config_data["db_pool_stress_delay_ms"] == 500
    assert config_data["db_pool_stress_affected_pool"] == "pool-a"
    print("✅ Scenario configuration verified")

    # Step 3: Generate traffic to both pools
    print("\n📝 Step 3: Generating traffic to both database pools...")
    traffic_count = 20

    for i in range(traffic_count):
        # Pool-A request
        response_a = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/accounts/alice.j@relibank.com",
            headers={"x-browser-user-id": TEST_USER_POOL_A},
            timeout=10
        )
        assert response_a.status_code == 200, f"Pool-A request {i+1} failed"

        # Pool-B request
        response_b = requests.get(
            f"{ACCOUNTS_SERVICE_URL}/accounts-service/accounts/bob.w@relibank.com",
            headers={"x-browser-user-id": TEST_USER_POOL_B},
            timeout=10
        )
        assert response_b.status_code == 200, f"Pool-B request {i+1} failed"

        if (i + 1) % 5 == 0:
            print(f"   Sent {i+1}/{traffic_count} requests to each pool...")

        time.sleep(0.3)

    print(f"✅ Generated {traffic_count} requests to each pool (total: {traffic_count * 2})")

    # Step 4: Wait for data to reach New Relic
    print("\n📝 Step 4: Waiting for data to reach New Relic...")
    wait_time = 120  # 2 minutes
    print(f"   Waiting {wait_time} seconds for telemetry data...")
    time.sleep(wait_time)
    print("✅ Wait complete")

    # Step 5: Validate custom attributes in New Relic
    print("\n📝 Step 5: Validating custom attributes in New Relic...")

    # Query for db.pool_id (custom attributes don't get custom. prefix when using add_custom_attribute)
    nrql = """
    SELECT count(*), uniques(db.pool_id)
    FROM Transaction
    WHERE appName LIKE '%Accounts Service%'
      AND db.pool_id IS NOT NULL
    SINCE 10 minutes ago
    """

    results = query_nerdgraph(nrql)
    assert results is not None, "Failed to query New Relic"
    assert len(results) > 0, "No results from New Relic query"

    count = results[0].get("count", 0)
    pools = results[0].get("uniques.db.pool_id", [])

    print(f"   Found {count} transactions with db.pool_id")
    print(f"   Detected pools: {', '.join(pools)}")

    assert count > 0, "No transactions found with db.pool_id attribute in New Relic"
    assert "pool-a" in pools, "pool-a not found in New Relic data"
    assert "pool-b" in pools, "pool-b not found in New Relic data"
    print("✅ Custom attributes validated in New Relic")

    # Step 6: Validate performance difference
    print("\n📝 Step 6: Validating performance difference between pools...")

    perf_nrql = """
    SELECT
      average(duration) as 'avg_duration',
      count(*) as 'count'
    FROM Transaction
    WHERE appName LIKE '%Accounts Service%'
      AND db.pool_id IS NOT NULL
    FACET db.pool_id
    SINCE 10 minutes ago
    """

    perf_results = query_nerdgraph(perf_nrql)
    assert perf_results is not None, "Failed to query performance data"
    assert len(perf_results) >= 2, f"Expected 2 pools, got {len(perf_results)}"

    pool_a_data = None
    pool_b_data = None

    for result in perf_results:
        pool = result.get("facet")
        if pool == "pool-a":
            pool_a_data = result
        elif pool == "pool-b":
            pool_b_data = result

    assert pool_a_data is not None, "No performance data for pool-a"
    assert pool_b_data is not None, "No performance data for pool-b"

    pool_a_avg = pool_a_data.get("avg_duration", 0)
    pool_b_avg = pool_b_data.get("avg_duration", 0)

    print(f"   Pool-A average duration: {pool_a_avg:.3f}s")
    print(f"   Pool-B average duration: {pool_b_avg:.3f}s")

    diff = pool_a_avg - pool_b_avg
    print(f"   Performance difference: {diff:.3f}s")

    # Pool-A should be approximately 500ms (0.5s) slower
    assert diff > 0.3, f"Pool-A is not significantly slower than Pool-B (diff: {diff:.3f}s)"
    assert diff < 0.8, f"Pool-A is too much slower than Pool-B (diff: {diff:.3f}s, expected ~0.5s)"
    print(f"✅ Performance difference matches expected 500ms delay")

    print("\n" + "=" * 70)
    print("✅ All E2E tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

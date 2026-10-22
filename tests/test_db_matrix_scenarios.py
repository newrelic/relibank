"""Safe checks for the Database Performance Matrix scenarios (db-matrix acts 2-4).

Deliberately does NOT start any scenario: lock-contention blocks the Ledger table that
transaction-service writes to, and plan-regression drops a real index, so running them in the
shared daily suite could break the other tests. Real runs are exercised by the scenario's
workflow in sandbox/staging only. These tests cover registration, validation and idle state.
"""
import os

import pytest
import requests

SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
API = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/db-matrix"
SCENARIOS = ("lock-contention", "competing-query", "plan-regression")


def test_db_matrix_status_lists_all_scenarios():
    resp = requests.get(f"{API}/status", timeout=10)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) == set(SCENARIOS), data
    for name, snap in data.items():
        assert snap["scenario"] == name
        assert "running" in snap and "seconds_remaining" in snap and "stats" in snap
    print(f"✓ db-matrix status lists {sorted(data)}")


def test_db_matrix_plan_regression_index_present_when_idle():
    snap = requests.get(f"{API}/plan-regression/status", timeout=10).json()
    if snap["running"]:
        pytest.skip("plan-regression is running right now; the index is expected to be absent")
    # None means the DB was unreachable from the runner; only False is a real problem.
    assert snap["index_present"] is not False, (
        "IX_BankTxn_Account is missing while plan-regression is idle; "
        "POST /scenario-runner/api/db-matrix/reset restores it"
    )


def test_db_matrix_rejects_unknown_scenario():
    assert requests.post(f"{API}/not-a-scenario/start", timeout=10).status_code == 404
    assert requests.post(f"{API}/not-a-scenario/stop", timeout=10).status_code == 404
    assert requests.get(f"{API}/not-a-scenario/status", timeout=10).status_code == 404


@pytest.mark.parametrize("name,duration", [("lock-contention", 5), ("lock-contention", 601),
                                           ("competing-query", 301), ("plan-regression", 601)])
def test_db_matrix_rejects_out_of_range_duration(name, duration):
    """Out-of-range durations are refused before anything starts."""
    resp = requests.post(f"{API}/{name}/start", params={"duration": duration}, timeout=10)
    assert resp.status_code == 400, f"{name} duration={duration}: {resp.status_code} {resp.text}"

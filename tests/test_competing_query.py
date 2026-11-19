"""Safe checks for the Database Performance Matrix's Competing Query scenario (db-matrix act 3).

Deliberately does NOT start the scenario by default: it runs for up to 5 minutes and competes
for CPU/IO, so running it in the shared daily suite could affect other tests. Real runs are
exercised by the scenario's workflow in sandbox/staging only.
"""
import os

import pytest
import requests

SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
API = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/db-matrix"


def test_competing_query_listed_in_status():
    resp = requests.get(f"{API}/status", timeout=10)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "competing-query" in data, data
    snap = data["competing-query"]
    assert snap["scenario"] == "competing-query"
    assert "running" in snap and "seconds_remaining" in snap and "stats" in snap


def test_competing_query_idle_when_nothing_running():
    snap = requests.get(f"{API}/competing-query/status", timeout=10).json()
    if snap["running"]:
        pytest.skip("competing-query is running right now; idle assertions don't apply")
    assert not snap["running"]


@pytest.mark.parametrize("duration", [5, 301])
def test_competing_query_rejects_out_of_range_duration(duration):
    """Out-of-range durations are refused before anything starts."""
    resp = requests.post(f"{API}/competing-query/start", params={"duration": duration}, timeout=10)
    assert resp.status_code == 400, f"duration={duration}: {resp.status_code} {resp.text}"


def test_db_matrix_rejects_unknown_scenario():
    """Generic db-matrix API check, not specific to this scenario."""
    assert requests.post(f"{API}/not-a-scenario/start", timeout=10).status_code == 404
    assert requests.post(f"{API}/not-a-scenario/stop", timeout=10).status_code == 404
    assert requests.get(f"{API}/not-a-scenario/status", timeout=10).status_code == 404

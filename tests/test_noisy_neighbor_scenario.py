"""Safe checks for the Noisy Neighbour scenario (/noisy-neighbor/*).

Deliberately does NOT start the scenario: it saturates CPU on the node that runs the payment
services, which would disturb the other tests in the shared daily suite. Real runs are exercised by
the scenario's workflow in sandbox/staging only. These tests cover validation, the dry run (which
creates nothing) and the idle state.
"""
import os

import pytest
import requests

SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
API = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/noisy-neighbor"


def test_noisy_neighbor_status_shape():
    resp = requests.get(f"{API}/status", timeout=15)
    assert resp.status_code == 200, resp.text
    snap = resp.json()
    assert snap["scenario"] == "noisy-neighbor"
    assert "running" in snap and "seconds_remaining" in snap and "exists" in snap
    print(f"✓ noisy-neighbor status: running={snap['running']} exists={snap['exists']}")


def test_noisy_neighbor_idle_when_suite_runs():
    snap = requests.get(f"{API}/status", timeout=15).json()
    if snap["running"]:
        pytest.skip("noisy-neighbor is running right now (a workflow started it)")
    assert snap["exists"] in (False, None), (
        "A noisy-neighbor Deployment exists while the scenario is idle (orphan?). "
        "POST /noisy-neighbor/reset removes it.")


@pytest.mark.parametrize("duration", [30, 1801])
def test_noisy_neighbor_rejects_out_of_range_duration(duration):
    resp = requests.post(f"{API}/start", params={"duration": duration}, timeout=15)
    assert resp.status_code == 400, f"duration={duration}: {resp.status_code} {resp.text}"


def test_noisy_neighbor_dry_run_creates_nothing():
    resp = requests.post(f"{API}/start", params={"dry_run": "true"}, timeout=30)
    if resp.status_code == 503:
        pytest.skip(f"cluster state not readable (RBAC not applied yet?): {resp.text}")
    if resp.status_code == 409:
        pytest.skip(f"start refused (another scenario running, or no headroom): {resp.text}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dry_run"] is True and body["plan"]["node"], body
    snap = requests.get(f"{API}/status", timeout=15).json()
    assert snap["running"] is False and snap["exists"] in (False, None), snap
    print(f"✓ dry run planned node {body['plan']['node']} with {body['plan']['headroom']['free_m']}m free")

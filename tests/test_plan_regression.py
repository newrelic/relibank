"""Safe checks for the Database Performance Matrix's Plan Regression scenario (db-matrix act 4).

Deliberately does NOT start the scenario by default: it drops a real index, so running it in the
shared daily suite could break other tests. Real runs are exercised by the scenario's workflow in
sandbox/staging only. Live-gated tests at the bottom exercise an actual run; they're opted in via
RUN_DBMATRIX_LIVE_TESTS=1, set only by that workflow's dedicated verification step.
"""
import os
import time

import pyodbc
import pytest
import requests

SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
API = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/db-matrix"

DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")
CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};"
    f"UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"
)

RUN_DBMATRIX_LIVE_TESTS = os.getenv("RUN_DBMATRIX_LIVE_TESTS", "").lower() in ("1", "true")
_live = pytest.mark.skipif(
    not RUN_DBMATRIX_LIVE_TESTS,
    reason="starts a live db-matrix scenario; only run in a dedicated sandbox verification pass "
           "(set RUN_DBMATRIX_LIVE_TESTS=1)",
)


def test_plan_regression_listed_in_status():
    resp = requests.get(f"{API}/status", timeout=10)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "plan-regression" in data, data
    snap = data["plan-regression"]
    assert snap["scenario"] == "plan-regression"
    assert "running" in snap and "seconds_remaining" in snap and "stats" in snap
    assert "preflight_orphan_check" in snap and "postflight_orphan_check" in snap


def test_plan_regression_idle_when_nothing_running():
    snap = requests.get(f"{API}/plan-regression/status", timeout=10).json()
    if snap["running"]:
        pytest.skip("plan-regression is running right now; idle assertions don't apply")
    assert snap["index_restore_error"] is None, (
        f"plan-regression's last run left a restore error: {snap['index_restore_error']}"
    )
    # None means the DB was unreachable from the runner; only False is a real problem.
    assert snap["index_present"] is not False, (
        "IX_BankTxn_Account is missing while plan-regression is idle; "
        "POST /scenario-runner/api/db-matrix/reset restores it"
    )
    if snap["postflight_orphan_check"] is not None:
        assert not snap["postflight_orphan_check"]["kill_errors"], (
            f"plan-regression's last post-flight orphan clear had kill errors: {snap['postflight_orphan_check']}"
        )


@pytest.mark.parametrize("duration", [5, 601])
def test_plan_regression_rejects_out_of_range_duration(duration):
    """Out-of-range durations are refused before anything starts."""
    resp = requests.post(f"{API}/plan-regression/start", params={"duration": duration}, timeout=10)
    assert resp.status_code == 400, f"duration={duration}: {resp.status_code} {resp.text}"


def _wait_until_idle(timeout: int = 650) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snap = requests.get(f"{API}/plan-regression/status", timeout=10).json()
        if not snap["running"]:
            return snap
        time.sleep(3)
    raise TimeoutError(f"plan-regression did not finish within {timeout}s")


@_live
def test_plan_regression_index_restored_after_run():
    """A normal run drops the index, flips the plan, and always restores the index on completion."""
    resp = requests.post(f"{API}/plan-regression/start", params={"duration": 30}, timeout=10)
    assert resp.status_code == 200, resp.text
    snap = _wait_until_idle()
    assert snap["stats"]["index_dropped"] is True, snap
    assert snap["index_present"] is True, snap
    assert snap["index_restore_error"] is None, snap


@_live
def test_plan_regression_retries_when_drop_blocked():
    """DROP INDEX retries under a short lock timeout when another session holds a table lock."""
    blocker = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    try:
        blocker.execute("BEGIN TRAN; SELECT TOP 1 * FROM BankTransactions WITH (TABLOCKX, HOLDLOCK);")
        resp = requests.post(f"{API}/plan-regression/start", params={"duration": 30}, timeout=10)
        assert resp.status_code == 200, resp.text
        time.sleep(10)
        snap = requests.get(f"{API}/plan-regression/status", timeout=10).json()
        assert snap["stats"].get("drop_attempts", 0) > 1 or snap["stats"].get("drop_lock_timeouts", 0) > 0, snap
    finally:
        blocker.rollback()
        blocker.close()
    _wait_until_idle()


@_live
def test_dbmatrix_orphan_guard_detects_and_clears_stuck_session():
    """Exercises the orphan-session find/kill logic directly against a real stuck session,
    reproducing the actual incident profile (ASYNC_NETWORK_IO + an OBJECT lock on
    BankTransactions, from an undrained result set). Calls the service's own functions
    in-process rather than through the HTTP API: the deployed service runs in a separate
    process/pod this test can't threshold-patch from here, so this verifies the DMV
    query/KILL logic itself, not the HTTP wiring (covered by the status-field checks above).
    """
    try:
        from scenario_service import scenario_service as svc
    except ImportError:
        pytest.skip("scenario_service module not importable from this test environment")

    original_threshold = svc.DBMATRIX_ORPHAN_WAIT_THRESHOLD_SECONDS
    svc.DBMATRIX_ORPHAN_WAIT_THRESHOLD_SECONDS = 2  # don't wait the real 5 minutes in CI

    orphan = pyodbc.connect(CONNECTION_STRING, autocommit=True, timeout=10)
    orphan_cursor = orphan.cursor()
    try:
        orphan_cursor.execute("BEGIN TRAN; SELECT * FROM BankTransactions WITH (HOLDLOCK);")
        # Deliberately never fetch -- the undrained result set is what puts the session into
        # ASYNC_NETWORK_IO, same as the real leaked connections that caused this.
        time.sleep(5)  # longer than the patched 2s threshold

        found = svc._dbmatrix_find_orphan_sessions()
        assert found, "expected the stuck session to be detected"

        cleared = svc._dbmatrix_clear_orphan_sessions()
        assert cleared["killed"], cleared
        assert not cleared["kill_errors"], cleared
    finally:
        svc.DBMATRIX_ORPHAN_WAIT_THRESHOLD_SECONDS = original_threshold
        try:
            orphan_cursor.close()
            orphan.close()
        except Exception:
            pass  # likely already severed by the KILL above

"""Gateway telemetry test (NR-638736): read-only NRQL against the environment under test.

Reads the last archive throttling run from the scenario service (T0 = when throttling went on, plus when it was reset)
and asks New Relic what the gateway did, minute by minute. It checks a healthy baseline before T0, then each failure
stage by its deadline (see gateway_stages.py), then the recovery after the reset. A missed stage fails naming the stage
and the value seen. The test never switches anything: a run is started and ended by someone else.

The negative control looks at a window with throttling off and needs zero failures, drops and refusals while logs are
flowing. It is what shows the checks above can fail: the same measures that stay quiet here light up in a run.

Needs NEW_RELIC_USER_API_KEY and NEW_RELIC_ACCOUNT_ID (the account that holds the gateway's telemetry); skipped without
them. Everything that depends on a run is skipped when there is no run to judge, or it is too short or too recent.

Good to know
- The run is read when pytest collects the tests, not when they run. test_archive_throttling_scenarios.py resets the
  switch at the start and end of every test, which rewrites the last run's times (and would switch off a run in
  progress), so the run would already be gone.
- The scenario service forgets the run when it restarts. To judge an older run, set GATEWAY_RUN_START (epoch seconds)
  and GATEWAY_RUN_RESET (epoch seconds, left out while it is still on).
- Optional: GATEWAY_BASELINE_PER_MIN (1200), GATEWAY_CONTROL_MINUTES (20), GATEWAY_ARCHIVE_EXPORTER and
  GATEWAY_EXPORTER_ATTRIBUTE (otlphttp/archive and exporter), NERDGRAPH_URL.
"""

import os
import time

import pytest
import requests

from gateway_stages import (
    ARCHIVE_EXPORTER,
    BASELINE_MINUTES,
    BASELINE_PER_MIN,
    EXPORTER_ATTRIBUTE,
    RECOVERY_AFTER_RESET_MIN,
    TOLERANCE_MIN,
    archive_exporter_query,
    baseline_nr_logs,
    baseline_problems,
    evaluate_recovery,
    evaluate_stage,
    exporters_query,
    failure_stages,
    merge_minutes,
    minutes_before_t0,
    new_relic_logs_query,
    received_query,
    recovery_not_yet_judgeable,
    too_short_to_judge,
)

SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY", "")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "")
NERDGRAPH_URL = os.getenv("NERDGRAPH_URL", "https://api.newrelic.com/graphql")
TARGET_COLOR = os.getenv("TARGET_COLOR", "").strip()

EXPECTED_PER_MIN = float(os.getenv("GATEWAY_BASELINE_PER_MIN", BASELINE_PER_MIN))
CONTROL_MINUTES = int(os.getenv("GATEWAY_CONTROL_MINUTES", "20"))
EXPORTER_ATTR = os.getenv("GATEWAY_EXPORTER_ATTRIBUTE", EXPORTER_ATTRIBUTE)
ARCHIVE = os.getenv("GATEWAY_ARCHIVE_EXPORTER", ARCHIVE_EXPORTER)

DATA_DELAY_MIN = 2  # New Relic takes a minute or two to show the newest minutes, so they are left out
MAX_MINUTES = 360  # one TIMESERIES query returns at most 366 buckets

HAS_NEW_RELIC = bool(NEW_RELIC_API_KEY and NEW_RELIC_ACCOUNT_ID)
pytestmark = pytest.mark.skipif(not HAS_NEW_RELIC, reason="NEW_RELIC_USER_API_KEY / NEW_RELIC_ACCOUNT_ID not set")


def read_run_state():
    """The last throttling run: {"t0", "reset", "enabled", "source"}, times in epoch seconds. None if unreadable."""
    start, reset = os.getenv("GATEWAY_RUN_START"), os.getenv("GATEWAY_RUN_RESET")
    if start:
        return {"t0": float(start), "reset": float(reset) if reset else None, "enabled": not reset, "source": "env"}
    # conftest.py adds X-Test-Env only once the tests run, and this runs at collection, so add it here
    headers = {"X-Test-Env": TARGET_COLOR} if TARGET_COLOR else {}
    url = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/archive-throttling/config"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        config = response.json()["scenarios"] if response.status_code == 200 else None
    except (requests.RequestException, ValueError, KeyError):
        config = None
    if config is None:
        return None
    return {
        "t0": config.get("enabled_at"),
        "reset": config.get("reset_at"),
        "enabled": bool(config.get("enabled")),
        "source": "scenario service",
    }


RUN = read_run_state() if HAS_NEW_RELIC else None


def query_nerdgraph(nrql: str) -> list:
    """Run one NRQL query through NerdGraph and return its rows."""
    query = "query($account: Int!, $nrql: Nrql!) { actor { account(id: $account) { nrql(query: $nrql) { results } } } }"
    response = requests.post(
        NERDGRAPH_URL,
        json={"query": query, "variables": {"account": int(NEW_RELIC_ACCOUNT_ID), "nrql": nrql}},
        headers={"API-Key": NEW_RELIC_API_KEY, "Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    assert "errors" not in body, f"NerdGraph rejected the query\n  {nrql}\n  {body['errors']}"
    return body["data"]["actor"]["account"]["nrql"]["results"]


def fetch_minutes(t0: float, start_s: float, end_s: float):
    return merge_minutes(
        t0,
        query_nerdgraph(received_query(start_s, end_s)),
        query_nerdgraph(archive_exporter_query(start_s, end_s, EXPORTER_ATTR, ARCHIVE)),
        query_nerdgraph(new_relic_logs_query(start_s, end_s)),
    )


@pytest.fixture(scope="module")
def run():
    if RUN is None:
        pytest.skip("the last run could not be read from the scenario service, and GATEWAY_RUN_START is not set")
    if RUN["t0"] is None:
        pytest.skip(
            "no archive throttling run since the scenario service started "
            "(it forgets runs when it restarts; set GATEWAY_RUN_START to judge an older one)"
        )
    return RUN


@pytest.fixture(scope="module")
def minutes(run):
    """Every minute from the baseline before T0 to the recovery after the reset, one query set for the whole module."""
    start = run["t0"] - (BASELINE_MINUTES + 1) * 60
    after_reset = (RECOVERY_AFTER_RESET_MIN + TOLERANCE_MIN + 5) * 60
    end = time.time() if run["reset"] is None else min(time.time(), run["reset"] + after_reset)
    end = min(end - DATA_DELAY_MIN * 60, start + MAX_MINUTES * 60)
    end = start + ((end - start) // 60) * 60  # whole minutes, so every bucket is complete
    return fetch_minutes(run["t0"], start, end)


def throttle_minutes_of(run) -> float:
    return ((run["reset"] or time.time()) - run["t0"]) / 60


def test_the_archive_exporter_can_be_told_apart_from_the_new_relic_exporter():
    rows = query_nerdgraph(exporters_query(EXPORTER_ATTR))
    seen = (rows[0].get("exporters") if rows else None) or []
    assert ARCHIVE in seen, (
        f"no gateway metric has {EXPORTER_ATTR} = '{ARCHIVE}'; the values seen in the last 24 hours are {seen}. "
        "The archive-side measures here and the gateway alerts filter on it, so correct the name where they differ."
    )


def test_the_baseline_before_throttling_is_healthy(run, minutes):
    problems = baseline_problems(minutes_before_t0(minutes), EXPECTED_PER_MIN)
    assert not problems, "the baseline before T0 is not healthy: " + "; ".join(problems)


@pytest.mark.parametrize(
    "key", ["export_failures", "queue_saturation", "queue_drops", "receiver_refused", "new_relic_gap"]
)
def test_each_failure_stage_is_reached_by_its_deadline(key, run, minutes):
    baseline_logs = baseline_nr_logs(minutes)
    stage = next(s for s in failure_stages(baseline_logs) if s.key == key)
    throttle_minutes = throttle_minutes_of(run)
    reason = too_short_to_judge(stage, throttle_minutes)
    if reason:
        pytest.skip(reason)
    if key == "new_relic_gap":
        assert baseline_logs > 0, "no New Relic-bound logs ('audit event' / 'other event') before T0 to compare against"
    verdict = evaluate_stage(minutes, stage, None if run["reset"] is None else throttle_minutes)
    assert verdict.ok, verdict.describe()


def test_the_gateway_is_back_to_baseline_after_the_reset(run, minutes):
    if run["reset"] is None:
        pytest.skip("throttling has not been reset yet")
    reset_min = (run["reset"] - run["t0"]) / 60
    reason = recovery_not_yet_judgeable(minutes, reset_min)
    if reason:
        pytest.skip(reason)
    ok, message = evaluate_recovery(minutes, reset_min, EXPECTED_PER_MIN)
    assert ok, message


def test_negative_control_with_throttling_off_shows_no_failures_drops_or_refusals():
    if RUN is None:
        pytest.skip("the last run could not be read from the scenario service")
    if RUN["enabled"]:
        pytest.skip("throttling is on right now, so this window is not a control")
    end = time.time() - DATA_DELAY_MIN * 60
    start = end - CONTROL_MINUTES * 60
    last_throttled = RUN["reset"] or RUN["t0"]
    if last_throttled is not None and last_throttled >= start - 60:
        pytest.skip(
            f"throttling was last on {(time.time() - last_throttled) / 60:.0f} min ago; "
            f"the control needs {CONTROL_MINUTES} min of throttling-off data before the last {DATA_DELAY_MIN}"
        )
    problems = baseline_problems(fetch_minutes(start, start, end), EXPECTED_PER_MIN)
    assert not problems, (
        f"negative control: throttling was off for the last {CONTROL_MINUTES} min and the gateway should look healthy, "
        "but " + "; ".join(problems)
    )

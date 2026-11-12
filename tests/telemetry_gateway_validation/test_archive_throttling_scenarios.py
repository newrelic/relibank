"""Scenario API tests for archive throttling (NR-638736).

archive-throttling makes compliance-archive answer 429/503 + Retry-After, which backs up the telemetry gateway's
archive queue. These tests only exercise the scenario-service API (config / toggle / reset): they check the switch,
not the archive or the gateway, and every test leaves throttling off.

Color-directed like the rest of the suite: conftest.py adds X-Test-Env when TARGET_COLOR is set, so the switch that
is flipped belongs to the color under test.
"""

import os

import pytest
import requests

SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
API = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/archive-throttling"
RATE_LIMIT_URL = f"{SCENARIO_SERVICE_URL}/scenario-runner/api/chaos-rate-limit-status"

DEFAULT_SETTINGS = {"enabled": False, "retry_after_seconds": 2, "share_503": 0.3}
# The cooldown countdown and can_trigger_new change with the clock, so only the stored counters are compared
RATE_LIMIT_STORED_FIELDS = ["last_trigger_time", "active_experiments", "max_concurrent", "cooldown_minutes"]


def get_config() -> dict:
    response = requests.get(f"{API}/config", timeout=10)
    assert response.status_code == 200, f"config returned {response.status_code}: {response.text}"
    body = response.json()
    assert body["status"] == "success"
    return body["scenarios"]


def toggle(**params) -> requests.Response:
    return requests.post(f"{API}/toggle", params=params, timeout=10)


def reset() -> dict:
    response = requests.post(f"{API}/reset", timeout=10)
    assert response.status_code == 200, f"reset returned {response.status_code}: {response.text}"
    body = response.json()
    assert body["status"] == "success"
    return body["scenarios"]


def settings_of(config: dict) -> dict:
    return {key: config[key] for key in DEFAULT_SETTINGS}


@pytest.fixture(autouse=True)
def throttling_off():
    """Start and finish every test with throttling off, because it changes how the archive answers."""
    # The daily scheduled run also targets environments that do not have archive throttling yet, because it ships one
    # environment at a time. Remove this skip once every environment has it, so a missing endpoint fails loudly.
    if requests.get(f"{API}/config", timeout=10).status_code == 404:
        pytest.skip("archive throttling is not deployed in this environment")
    reset()
    yield
    try:
        reset()
    except Exception:
        pass  # Ignore cleanup errors


def test_reset_gives_default_settings():
    config = get_config()
    assert settings_of(config) == DEFAULT_SETTINGS


def test_toggle_on_is_stored_and_persists_between_calls():
    response = toggle(enabled="true", retry_after=7, share_503=0.5)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success", body

    # A separate call sees the same state, so it is stored and not just echoed back
    config = get_config()
    assert config["enabled"] is True
    assert config["retry_after_seconds"] == 7
    assert config["share_503"] == 0.5
    assert isinstance(config["enabled_at"], (int, float)) and config["enabled_at"] > 0
    assert config["reset_at"] is None


def test_changing_settings_of_a_run_in_progress_keeps_its_start_time():
    first = toggle(enabled="true", retry_after=2, share_503=0.3).json()["scenarios"]
    second = toggle(enabled="true", retry_after=9, share_503=1).json()["scenarios"]

    assert second["enabled_at"] == first["enabled_at"], "the start time (T0 for the gateway tests) moved"
    assert second["retry_after_seconds"] == 9
    assert second["share_503"] == 1


def test_toggle_off_records_the_reset_time_and_keeps_the_start_time():
    started = toggle(enabled="true").json()["scenarios"]
    stopped = toggle(enabled="false").json()["scenarios"]

    assert stopped["enabled"] is False
    assert stopped["enabled_at"] == started["enabled_at"]
    assert stopped["reset_at"] >= stopped["enabled_at"]
    assert get_config()["enabled"] is False


def test_reset_clears_the_switch_and_the_settings():
    toggle(enabled="true", retry_after=30, share_503=0.9)
    cleared = reset()

    assert settings_of(cleared) == DEFAULT_SETTINGS
    assert settings_of(get_config()) == DEFAULT_SETTINGS
    # The last run's start and stop times stay, because the gateway tests read them after the reset
    assert cleared["enabled_at"] is not None
    assert cleared["reset_at"] is not None


def test_turning_it_on_again_starts_a_new_run():
    toggle(enabled="true")
    toggle(enabled="false")
    again = toggle(enabled="true").json()["scenarios"]

    assert again["enabled"] is True
    assert again["reset_at"] is None, "a new run must not carry the previous run's reset time"


@pytest.mark.parametrize(
    "params",
    [
        {"retry_after": -1},
        {"retry_after": 61},
        {"share_503": -0.1},
        {"share_503": 1.5},
    ],
)
def test_out_of_range_values_are_rejected_and_change_nothing(params):
    toggle(enabled="true", retry_after=5, share_503=0.4)
    before = get_config()

    response = toggle(enabled="true", **params)

    assert response.status_code == 200
    assert response.json()["status"] == "error", f"{params} was accepted: {response.text}"
    assert get_config() == before


@pytest.mark.parametrize(
    "params",
    [
        {"enabled": "true", "retry_after": "soon"},
        {"enabled": "true", "share_503": "half"},
        {"enabled": "maybe"},
        {},  # enabled is required
    ],
)
def test_values_of_the_wrong_type_are_rejected(params):
    response = toggle(**params)
    assert response.status_code == 422, f"{params} returned {response.status_code}: {response.text}"
    assert get_config()["enabled"] is False


@pytest.mark.parametrize("retry_after,share_503", [(0, 0), (60, 1), (0, 1), (60, 0)])
def test_the_edges_of_the_allowed_range_are_accepted(retry_after, share_503):
    response = toggle(enabled="true", retry_after=retry_after, share_503=share_503)
    assert response.json()["status"] == "success"
    config = get_config()
    assert (config["retry_after_seconds"], config["share_503"]) == (retry_after, share_503)


def test_the_chaos_rate_limiter_is_never_touched():
    def snapshot() -> dict:
        response = requests.get(RATE_LIMIT_URL, timeout=10)
        assert response.status_code == 200
        body = response.json()
        return {key: body[key] for key in RATE_LIMIT_STORED_FIELDS}

    before = snapshot()
    toggle(enabled="true", retry_after=5, share_503=0.5)
    toggle(enabled="true", retry_after=9, share_503=1)
    toggle(enabled="false")
    toggle(enabled="true", retry_after=61)  # rejected on purpose
    reset()

    assert snapshot() == before, "archive throttling changed the chaos rate limiter"

"""Tests for compliance-archive (NR-638736), run in-process: no cluster and no New Relic account needed.

Checks that the archive answers 200 when it is not throttled, answers a mix of 429 and 503 with Retry-After when it
is, and emits one ArchiveIngestRequest event per request. The scenario service and the New Relic agent are replaced
with fakes, so the test controls the throttle setting and sees every event.
"""

import asyncio
import gzip
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("newrelic")
pytest.importorskip("opentelemetry.proto.collector.logs.v1.logs_service_pb2")

from fastapi.testclient import TestClient  # noqa: E402
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "compliance_archive"))
import compliance_archive_service as archive  # noqa: E402

PROTOBUF = {"content-type": "application/x-protobuf"}


def otlp_body(records: int) -> bytes:
    request = ExportLogsServiceRequest()
    scope = request.resource_logs.add().scope_logs.add()
    for i in range(records):
        scope.log_records.add().body.string_value = f"audit event {i}"
    return request.SerializeToString()


@pytest.fixture(autouse=True)
def fresh_throttling_cache(monkeypatch):
    """Every test starts without a cached setting from the scenario service."""
    monkeypatch.setattr(
        archive,
        "_throttling_cache",
        {"checked_at": float("-inf"), "ok_at": float("-inf"), "value": archive.DEFAULT_THROTTLING},
    )


@pytest.fixture
def events(monkeypatch):
    """Every custom event the archive records, as (event type, attributes)."""
    recorded = []
    monkeypatch.setattr(
        archive.newrelic.agent, "record_custom_event", lambda name, params: recorded.append((name, params))
    )
    return recorded


@pytest.fixture
def client():
    return TestClient(archive.app)


@pytest.fixture
def set_throttling(monkeypatch):
    """Make the archive see this throttle setting, as if the scenario service had returned it."""

    def apply(enabled=False, retry_after_seconds=2, share_503=0.3):
        setting = {"enabled": enabled, "retry_after_seconds": retry_after_seconds, "share_503": share_503}

        async def fake_get_archive_throttling():
            return setting

        monkeypatch.setattr(archive, "get_archive_throttling", fake_get_archive_throttling)

    return apply


def test_health_check(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --------------------------------------------------------------------------- not throttled


def test_answers_200_when_not_throttled(client, set_throttling):
    set_throttling(enabled=False)
    response = client.post("/v1/logs", content=otlp_body(10), headers=PROTOBUF)

    assert response.status_code == 200
    assert response.content == b"", "an empty body is a valid OTLP export response"
    assert "retry-after" not in response.headers


@pytest.mark.parametrize(
    "body,headers,expected_records",
    [
        (otlp_body(10), PROTOBUF, 10),
        (gzip.compress(otlp_body(4)), {**PROTOBUF, "content-encoding": "gzip"}, 4),
        (
            json.dumps({"resourceLogs": [{"scopeLogs": [{"logRecords": [{}, {}, {}]}]}]}).encode(),
            {"content-type": "application/json"},
            3,
        ),
        (b"", PROTOBUF, 0),
    ],
    ids=["protobuf", "gzipped protobuf", "json", "empty"],
)
def test_accepts_every_body_format_the_gateway_can_send(
    client, set_throttling, events, body, headers, expected_records
):
    set_throttling(enabled=False)
    response = client.post("/v1/logs", content=body, headers=headers)

    assert response.status_code == 200
    assert events[0][1]["records"] == expected_records


# --------------------------------------------------------------------------- throttled


def test_throttled_with_no_503_share_answers_429_with_retry_after(client, set_throttling):
    set_throttling(enabled=True, retry_after_seconds=7, share_503=0)
    response = client.post("/v1/logs", content=otlp_body(10), headers=PROTOBUF)

    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"


def test_throttled_with_all_503_answers_503_with_retry_after(client, set_throttling):
    set_throttling(enabled=True, retry_after_seconds=3, share_503=1)
    response = client.post("/v1/logs", content=otlp_body(10), headers=PROTOBUF)

    assert response.status_code == 503
    assert response.headers["retry-after"] == "3"


def test_throttled_answers_a_mix_of_429_and_503_in_the_configured_share(client, set_throttling, monkeypatch):
    set_throttling(enabled=True, share_503=0.3)
    monkeypatch.setattr(archive.random, "random", random.Random(42).random)  # same sequence every run

    codes = [client.post("/v1/logs", content=otlp_body(1), headers=PROTOBUF).status_code for _ in range(500)]

    assert set(codes) == {429, 503}, "a throttled archive should answer with both codes"
    assert 0.2 <= codes.count(503) / len(codes) <= 0.4, (
        f"503 share was {codes.count(503) / len(codes):.2f}, expected about 0.3"
    )


def test_throttled_never_answers_200(client, set_throttling):
    set_throttling(enabled=True, share_503=0.5)
    codes = {client.post("/v1/logs", content=otlp_body(1), headers=PROTOBUF).status_code for _ in range(100)}
    assert 200 not in codes


# --------------------------------------------------------------------------- events


def test_emits_one_event_per_request(client, set_throttling, events):
    set_throttling(enabled=False)
    for _ in range(5):
        client.post("/v1/logs", content=otlp_body(10), headers=PROTOBUF)

    assert [name for name, _ in events] == ["ArchiveIngestRequest"] * 5


def test_event_describes_a_successful_request(client, set_throttling, events):
    set_throttling(enabled=False)
    body = otlp_body(10)
    client.post("/v1/logs", content=body, headers=PROTOBUF)

    ((name, attributes),) = events
    assert name == "ArchiveIngestRequest"
    assert attributes == {
        "status_code": 200,
        "throttled": False,
        "retry_after_seconds": 0,
        "records": 10,
        "content_type": "application/x-protobuf",
        "content_length": len(body),
    }


def test_event_describes_a_throttled_request(client, set_throttling, events):
    set_throttling(enabled=True, retry_after_seconds=7, share_503=1)
    response = client.post("/v1/logs", content=otlp_body(10), headers=PROTOBUF)

    ((_, attributes),) = events
    assert attributes["status_code"] == response.status_code == 503
    assert attributes["throttled"] is True
    assert attributes["retry_after_seconds"] == 7
    assert attributes["records"] == 10


def test_an_unreadable_body_is_still_answered_and_counted_as_minus_one(client, set_throttling, events):
    set_throttling(enabled=False)
    response = client.post("/v1/logs", content=b"\x00\xffnot otlp", headers=PROTOBUF)

    assert response.status_code == 200
    assert events[0][1]["records"] == -1


# --------------------------------------------------------------------------- reading the setting from the scenario service


class FakeScenarioService:
    """Stands in for httpx.AsyncClient and the scenario service behind it."""

    def __init__(self):
        self.mode = "up"  # up | down | error
        self.setting = {"enabled": True, "retry_after_seconds": 5, "share_503": 0.1}
        self.requests = 0

    def client_class(self):
        outer = self

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url, timeout=None):
                outer.requests += 1
                assert url.endswith("/scenario-runner/api/archive-throttling/config")
                if outer.mode == "down":
                    raise ConnectionError("scenario service unreachable")
                if outer.mode == "error":
                    return SimpleNamespace(status_code=500, json=lambda: {})
                return SimpleNamespace(status_code=200, json=lambda: {"status": "success", "scenarios": outer.setting})

        return FakeClient


@pytest.fixture
def scenario_service(monkeypatch):
    fake = FakeScenarioService()
    clock = SimpleNamespace(now=1000.0)
    monkeypatch.setattr(archive.httpx, "AsyncClient", fake.client_class())
    monkeypatch.setattr(archive, "time", SimpleNamespace(monotonic=lambda: clock.now))
    fake.clock = clock
    return fake


def current_setting():
    return asyncio.run(archive.get_archive_throttling())


def test_reads_the_setting_from_the_scenario_service(scenario_service):
    assert current_setting() == scenario_service.setting


def test_the_setting_is_cached_for_a_second(scenario_service):
    current_setting()
    scenario_service.clock.now += 0.5
    current_setting()
    assert scenario_service.requests == 1

    scenario_service.clock.now += 0.6  # more than a second since the first look
    current_setting()
    assert scenario_service.requests == 2


def test_a_change_in_the_scenario_service_shows_up_within_about_a_second(scenario_service):
    assert current_setting()["enabled"] is True
    scenario_service.setting = {"enabled": False, "retry_after_seconds": 2, "share_503": 0.3}
    scenario_service.clock.now += 1.1
    assert current_setting()["enabled"] is False


@pytest.mark.parametrize("failure", ["down", "error"])
def test_a_short_outage_keeps_the_last_known_setting(scenario_service, failure):
    assert current_setting()["enabled"] is True
    scenario_service.mode = failure
    scenario_service.clock.now += 5

    assert current_setting()["enabled"] is True, "a short blip must not end a run in progress"


@pytest.mark.parametrize("failure", ["down", "error"])
def test_a_long_outage_falls_back_to_not_throttled(scenario_service, failure):
    assert current_setting()["enabled"] is True
    scenario_service.mode = failure
    scenario_service.clock.now += 31

    assert current_setting() == archive.DEFAULT_THROTTLING
    assert current_setting()["enabled"] is False


def test_a_scenario_service_that_was_never_reachable_means_not_throttled(scenario_service):
    scenario_service.mode = "down"
    assert current_setting()["enabled"] is False

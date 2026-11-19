"""Ingest auth tests for the token-gated /otlp/ entrance (NR-638736).

The blue and green nginx proxies only let a request through to relibank-telemetry-gateway when it carries
`Authorization: Bearer <OTLP_INGEST_TOKEN>`. These tests send an empty OTLP export (no log is created) to the
deployed environment and check who gets in.

Needs BASE_URL (the environment's public URL) and OTLP_INGEST_TOKEN; without them (for example a local
`skaffold dev` run, which has no /otlp/ route) the whole module is skipped.

Color-directed like the rest of the suite: conftest.py adds X-Test-Env when TARGET_COLOR is set.
"""

import os

import pytest
import requests

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
TOKEN = os.getenv("OTLP_INGEST_TOKEN", "")
URL = f"{BASE_URL}/otlp/v1/logs"
EMPTY_EXPORT = '{"resourceLogs":[]}'

pytestmark = pytest.mark.skipif(
    not (BASE_URL and TOKEN),
    reason="needs BASE_URL and OTLP_INGEST_TOKEN (a deployed environment with the /otlp/ entrance)",
)


def send(authorization=None, extra_headers=None, method="POST") -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization
    headers.update(extra_headers or {})
    # No redirects: a redirect to https would hide whether the token check itself works
    return requests.request(method, URL, headers=headers, data=EMPTY_EXPORT, timeout=20, allow_redirects=False)


def test_a_request_without_a_token_is_rejected():
    response = send()
    assert response.status_code == 401, f"got {response.status_code}: {response.text[:200]}"
    assert "Bearer" in response.headers.get("WWW-Authenticate", "")


def test_a_wrong_token_is_rejected():
    assert send("Bearer not-the-token-0123456789").status_code == 401


def test_the_token_without_the_bearer_prefix_is_rejected():
    assert send(TOKEN).status_code == 401


def test_a_token_with_one_character_added_or_missing_is_rejected():
    assert send(f"Bearer {TOKEN}x").status_code == 401
    assert send(f"Bearer {TOKEN[:-1]}").status_code == 401


def test_the_token_must_match_exactly_including_letter_case():
    changed = TOKEN.swapcase()
    if changed == TOKEN:
        pytest.skip("the token has no letters, so there is no case to change")
    assert send(f"Bearer {changed}").status_code == 401


def test_reading_without_a_token_is_rejected_too():
    assert send(method="GET").status_code == 401


def test_the_right_token_is_accepted():
    response = send(f"Bearer {TOKEN}")
    assert response.status_code == 200, f"got {response.status_code}: {response.text[:200]}"


@pytest.fixture
def color(target_color):
    if not target_color:
        pytest.skip("TARGET_COLOR is not set, so there is no color route to check")
    return target_color


def test_the_color_route_needs_the_token_too(color):
    """X-Test-Env sends the request to one color's proxy; that proxy must check the token as well."""
    route = {"X-Test-Env": color}
    assert send(extra_headers=route).status_code == 401
    assert send("Bearer not-the-token-0123456789", extra_headers=route).status_code == 401


def test_the_color_route_accepts_the_right_token(color):
    assert send(f"Bearer {TOKEN}", extra_headers={"X-Test-Env": color}).status_code == 200

"""Shared pytest fixtures for the relibank test suite.

Color-directed testing (modeled on demogorgon): when the ``TARGET_COLOR`` env var is set,
every HTTP request the suite makes carries an ``X-Test-Env: <color>`` header so it routes
through relibank's canary ingress to that specific deployment color. The active color is
reached whether or not the header is present, so an empty ``TARGET_COLOR`` (e.g. the
scheduled cron run) simply exercises whatever color is live.

This is applied centrally by patching ``requests.Session.request`` in an autouse fixture,
so individual test modules need no changes — every ``requests.get``/``post`` (which use a
transient Session under the hood) picks it up. Adding the header to non-relibank calls
(e.g. the New Relic NerdGraph API) is harmless; unknown headers are ignored.
"""
import os

import pytest
import requests


@pytest.fixture(scope="session")
def target_color():
    """Deployment color the run is directed at; '' means active color / no routing."""
    return os.getenv("TARGET_COLOR", "").strip()


@pytest.fixture(autouse=True, scope="session")
def _route_requests_to_color(target_color):
    """Attach ``X-Test-Env: <color>`` to every request when a color is directed."""
    if not target_color:
        yield
        return

    original_request = requests.sessions.Session.request

    def request_with_color(self, method, url, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        headers.setdefault("X-Test-Env", target_color)  # explicit per-call header wins
        kwargs["headers"] = headers
        return original_request(self, method, url, **kwargs)

    requests.sessions.Session.request = request_with_color
    try:
        yield
    finally:
        requests.sessions.Session.request = original_request

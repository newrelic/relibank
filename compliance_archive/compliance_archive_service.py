"""compliance-archive: stand-in for a third-party audit-log archive vendor (NR-638736).

Receives OTLP/HTTP logs from the relibank-telemetry-gateway and answers 200. While the scenario service has
archive throttling switched on, it answers 429 or 503 with a Retry-After header instead, which backs up the
gateway's archive queue. Nothing is stored; it only counts what it was sent.
"""

import gzip
import json
import logging
import os
import random
import time
from typing import Any, Dict, Optional

import httpx
import newrelic.agent
from fastapi import FastAPI, Request, Response
from google.protobuf.message import DecodeError
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

newrelic.agent.initialize()

app = FastAPI(title="Compliance Archive")

# Scenario service URL (same variable and default as bill_pay)
SCENARIO_SERVICE_URL = os.getenv(
    "SCENARIO_SERVICE_URL", "http://scenario-runner-service.relibank.svc.cluster.local:8000"
)

# The throttling settings are read from the scenario service and cached this long, so a toggle takes effect
# within about a second without asking the scenario service for every request.
THROTTLING_CACHE_SECONDS = 1.0
# If the scenario service cannot be reached, keep the last known setting this long (a short blip must not end a
# run in progress), then fall back to "not throttled" so a long outage can never leave the archive stuck refusing.
THROTTLING_STALE_SECONDS = 30.0

DEFAULT_THROTTLING = {"enabled": False, "retry_after_seconds": 2, "share_503": 0.3}

_throttling_cache: Dict[str, Any] = {
    "checked_at": float("-inf"),  # last attempt, successful or not
    "ok_at": float("-inf"),  # last successful fetch
    "value": DEFAULT_THROTTLING,
}


async def get_archive_throttling() -> Dict[str, Any]:
    """Fetch archive throttling configuration from scenario service (cached for a second)"""
    now = time.monotonic()
    if now - _throttling_cache["checked_at"] < THROTTLING_CACHE_SECONDS:
        return _throttling_cache["value"]

    _throttling_cache["checked_at"] = now
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCENARIO_SERVICE_URL}/scenario-runner/api/archive-throttling/config",
                timeout=2.0,
            )
            if response.status_code == 200:
                _throttling_cache["value"] = response.json().get("scenarios", DEFAULT_THROTTLING)
                _throttling_cache["ok_at"] = now
    except Exception as e:
        logging.debug(f"Could not fetch archive throttling config: {e}")

    if now - _throttling_cache["ok_at"] > THROTTLING_STALE_SECONDS:
        _throttling_cache["value"] = DEFAULT_THROTTLING
    return _throttling_cache["value"]


def count_log_records(body: bytes, content_type: str, content_encoding: str) -> Optional[int]:
    """Count the log records in an OTLP/HTTP export request. Returns None if the body cannot be read."""
    try:
        if "gzip" in content_encoding:
            body = gzip.decompress(body)
        if "json" in content_type:
            payload = json.loads(body or b"{}")
            return sum(
                len(scope.get("logRecords", []))
                for resource in payload.get("resourceLogs", [])
                for scope in resource.get("scopeLogs", [])
            )
        request = ExportLogsServiceRequest()
        request.ParseFromString(body)
        return sum(len(scope.log_records) for resource in request.resource_logs for scope in resource.scope_logs)
    except (OSError, EOFError, ValueError, DecodeError) as e:
        logging.warning(f"Could not read OTLP request body: {e}")
        return None


@app.get("/healthz")
async def healthz():
    """Health check endpoint"""
    return {"status": "ok"}


@app.post("/v1/logs")
async def ingest_logs(request: Request):
    """OTLP/HTTP logs endpoint: 200 normally, 429 or 503 plus Retry-After while throttled"""
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    records = count_log_records(body, content_type, request.headers.get("content-encoding", ""))

    throttling = await get_archive_throttling()
    throttled = bool(throttling.get("enabled", False))
    retry_after = int(throttling.get("retry_after_seconds", 2))
    status_code = 200
    if throttled:
        status_code = 503 if random.random() < float(throttling.get("share_503", 0.3)) else 429

    newrelic.agent.record_custom_event(
        "ArchiveIngestRequest",
        {
            "status_code": status_code,
            "throttled": throttled,
            "retry_after_seconds": retry_after if throttled else 0,
            "records": records if records is not None else -1,
            "content_type": content_type,
            "content_length": len(body),
        },
    )

    if throttled:
        return Response(status_code=status_code, headers={"Retry-After": str(retry_after)})
    # An empty body is a valid ExportLogsServiceResponse
    return Response(status_code=200, media_type="application/x-protobuf")

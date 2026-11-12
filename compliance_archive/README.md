# compliance-archive

Stand-in for a third-party audit-log archive vendor (NR-638736). FastAPI, port 5008, New Relic APM agent.
It receives OTLP/HTTP logs from the `relibank-telemetry-gateway`, counts them, stores nothing.

| Endpoint | Does |
|---|---|
| `POST /v1/logs` | OTLP/HTTP logs sink (protobuf or JSON, gzip accepted). `200` normally; `429` or `503` plus a `Retry-After` header while throttled. Emits one `ArchiveIngestRequest` event per request (`status_code`, `throttled`, `retry_after_seconds`, `records`, `content_type`, `content_length`). |
| `GET /healthz` | Health check. |

## Throttling

The switch lives in the scenario service (`/scenario-runner/api/archive-throttling/...`), not here. The archive reads it from
`SCENARIO_SERVICE_URL` and caches it for about a second, so a toggle takes effect within a second or two.

- Not reachable: the last known setting is kept for 30 s (a short blip must not end a run), then the archive falls back to "not throttled".
- An unreadable request body is still answered `200` (`records` is `-1`).

## Run it locally

```bash
cd compliance_archive
pip install -r requirements.txt
SCENARIO_SERVICE_URL=http://localhost:8000 NEW_RELIC_MONITOR_MODE=false uvicorn compliance_archive_service:app --port 5008
```

With `skaffold dev` it comes up from `k8s/overlays/dev/compliance-archive.yaml`. In AKS it is an entry in the Terraform `services` map
(`catapult-service`).

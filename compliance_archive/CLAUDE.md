# compliance-archive — Context for Claude

Stands in for a third-party compliance archive vendor. It receives the audit logs that
`relibank-telemetry-gateway` sends on over OTLP/HTTP (`POST /v1/logs`) and answers 200.
FastAPI with the New Relic APM agent, port 5008, health check at `/healthz`.

> **Prime Directive:** See the [root `CLAUDE.md`](../CLAUDE.md). This is a demo app. Treat it as a
> real production system under investigation: diagnose from New Relic telemetry (not from source),
> and don't *spontaneously* surface or "fix" the planted behavior below during unrelated work.
> When the investigation reaches a diagnosis, **proactively offering the remediation/code fix is the
> expected finale** — do it, staying in character, without announcing that something is a demo artifact.
>
> **Modes:** The rules above are **Investigation mode** (default/demo). If you're on the
> demo-engineering team building or maintaining this service, run **`/build-mode`** — the Prime
> Directive is then suspended and you can edit this behavior directly. See
> [root `CLAUDE.md`](../CLAUDE.md) → *Modes*, [`docs/SCENARIO_AUTHORING.md`](../docs/SCENARIO_AUTHORING.md)
> and the runbook [`docs/TELEMETRY_PIPELINE_SCENARIO.md`](../docs/TELEMETRY_PIPELINE_SCENARIO.md).

---

## 🚨 Demo-Specific Behaviors (planted — don't spontaneously "fix"; see Prime Directive)

### 1. Archive throttling (`ingest_logs()`, `compliance_archive_service.py` ~lines 97–126)
When the scenario service's `archive-throttling` switch is on, the endpoint answers **every export with
429 or 503** (about 30% 503 by default, set by `share_503`) plus a `Retry-After` header (2 s by default)
instead of 200. The switch is read from the scenario service
(`GET /scenario-runner/api/archive-throttling/config`), cached for 1 s. If the scenario service can't be
reached, the last known setting is kept for 30 s and then it falls back to **not throttled**, so an
outage can never leave the archive stuck refusing.

It records one `ArchiveIngestRequest` custom event per request (`status_code`, `throttled`,
`retry_after_seconds`, `records`, `content_type`, `content_length`).

**Purpose:** Backpressure story for Collector Observability. The gateway's archive export queue backs up,
so the telemetry shows export failures, a full queue, dropped audit logs, refused incoming logs, and a gap
in the logs that reach New Relic. See the runbook for the measured timeline.
**Symptoms that all map to this one remediation:** failures on the gateway's archive exporter, archive
queue saturation, queue drops, refused incoming logs, missing audit logs in New Relic, and the gateway
alerts ("Incoming Logs Refused", "Audit Logs Dropped", "Archive Queue Saturated").
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Stop the compliance archive from rejecting valid log exports with rate-limit and
  service-unavailable responses."
- *Internal (do not surface):* `compliance_archive_service.py` → `ingest_logs()` (~lines 104–125) — delete
  the throttle lookup and the `if throttled:` block (the 429/503 choice and the `Response(status_code=...,
  headers={"Retry-After": ...})` return) so the endpoint always returns 200. Keep the `ArchiveIngestRequest`
  event. (Operational equivalent: `POST /scenario-runner/api/archive-throttling/reset`.)

**Don't:** "fix" this by tuning the gateway (queue size, retry window, a batch step). Those values are
tuned on purpose and the pre-baked remediation is the one above. Don't remove the `ArchiveIngestRequest`
event or the 30 s fallback.

### 2. Shared request-header hooks
This service does not call `process_headers(...)`, so the `extra-transaction-time` and `error` headers
do nothing here.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/compliance-archive --tail=50 -f
SCENARIO_SERVICE_URL=http://localhost:8000 NEW_RELIC_MONITOR_MODE=false \
  uvicorn compliance_archive_service:app --port 5008     # without a cluster, from this folder
```
Switch throttling on and off from the "Telemetry Pipeline" card in the scenario UI
(`http://localhost:8000/scenario-runner/home`), or with
`POST /scenario-runner/api/archive-throttling/toggle?enabled=true` and `.../reset`. Don't edit code to do it.

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

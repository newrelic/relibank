# Telemetry Pipeline Scenario (collector backpressure)

**TL;DR:** A gateway collector (`relibank-telemetry-gateway`) takes audit and other logs from an external
producer, sends all of them to New Relic, and sends the audit logs to a stand-in archive vendor
(`compliance-archive`). When you switch **archive throttling** on, the archive starts answering 429/503, the
gateway backs up, and Collector Observability shows it fail in steps. Switch it off and the gateway heals
itself. Jira: NR-638736.

> **Audience & mode.** This is **Builder-mode** documentation for the demo-engineering team. Run
> **`/build-mode`** before working from it. In a live demo (any session that uses the New Relic MCP server)
> the root `CLAUDE.md` Prime Directive applies instead and these behaviors are left untouched.

---

## What it does

```
external producer ──▶ nginx proxy  /otlp/  (bearer token) ──▶ relibank-telemetry-gateway
(goblin-swarm loadgen)                                          │
                                                                ├─ all logs ───────────────▶ New Relic
                                                                └─ audit logs (log.type) ──▶ compliance-archive
                                                                                              ┆
                              scenario service: archive-throttling  ◀┄ archive reads it, 1 s ┄┘
```

With throttling **off** the archive answers 200 and nothing is wrong. With it **on**, the archive (which reads the
switch from the scenario service about once a second) answers every export with 429 or 503 plus `Retry-After`. The
gateway's archive queue fills, and because the archive path has no batch step, a full queue turns into refused
incoming requests, which also holds back the New Relic copy. The audit attribute (`log.type == "audit"`) is a
placeholder until the producer contract is settled (open item on NR-638736).

## Where the code lives (three repos)

| Repo | What | Where |
|---|---|---|
| **relibank** | Gateway config and image | `otel_collector_gateway/` |
| | Stand-in archive (FastAPI + APM) | `compliance_archive/` |
| | The switch: config, toggle, reset, and a "Telemetry Pipeline" card | `scenario_service/` |
| | Local run | `k8s/overlays/dev/`, `skaffold.yaml` |
| | Tests | `tests/telemetry_gateway_validation/`, option in `.github/workflows/test-suite.yml` |
| **catapult-service** | Gateway Deployment, archive in the services map, `/otlp/` in the blue/green proxies, image builds | `relibank_deployer/terraform/aks/`, `.github/workflows/` |
| | The gateway's config **as AKS runs it**: a hand-synced copy of `otel_collector_gateway/config.yaml` (plus a 4-line header). Change both | `relibank_deployer/terraform/aks/app_module/templates/otel-collector-gateway-config.yaml` |
| | The four alerts and the Slack route | `relibank_deployer/terraform/aks/newrelic/nr_alerts_telemetry_gateway.tf` |
| **goblin-swarm** | The traffic and the throttling schedule | `.github/workflows/relibank-telemetry-loadgen.yml`, `relibank/telemetry_loadgen/send_logs.sh` |

## What you should see (measured in two sandbox runs)

Minutes are counted from the moment throttling is switched on (T). The load is about 1,200 logs a minute
(960 audit, 240 other).

| When | What happens |
|---|---|
| Before T | Healthy: gateway receives 1,200 a minute, queue about 0%, refused / dropped / failed all 0 |
| T+2 | The archive exporter shows its first failed exports |
| T+5 | The gateway starts refusing incoming logs |
| T+6 | The archive queue is full (95% or more) and queue drops start. Logs reaching New Relic fall from about 1,200 to about 300 a minute, because the audit logs stop arriving |
| T+9.5 to T+12.5 | Slack alerts arrive: "Incoming Logs Refused", then "Audit Logs Dropped", then "Archive Queue Saturated" (it needs the queue full for 5 minutes, so it comes last) |
| Reset (T+20) | Throttling off. The gateway is back to baseline in 1 to 2 minutes |
| Reset + 4.5 to 6.7 min | The three alerts close |

"Not Recovered" (queue at 95% or more for 15 minutes) stays quiet in a 20-minute run. It fires only if
throttling is held for more than about 22 minutes.

## Run it

**The ticket's run, from GitHub (goblin-swarm):** Actions → `relibank-telemetry-loadgen` → Run workflow.
Pick the environment (and the color). The run is fixed: 12 minutes of baseline, throttling on for 20 minutes,
then off, 70 minutes in total. The job log prints the scenario service's own `enabled_at` and `reset_at` for
the switch-on and switch-off. **Tell `#demogorgon-alerts` first**, because three alerts fire.

**Then run the tests** (relibank → Actions → Relibank Test Suite → `test_suite` = `telemetry-gateway-validation`,
the same environment and color), best between minute 56 and 66 of the loadgen run. See *Tests* below.

**By hand:**

```bash
# Scenario UI card "Telemetry Pipeline": http://<host>/scenario-runner/home
curl -X POST -H 'X-Test-Env: green' "http://<host>/scenario-runner/api/archive-throttling/toggle?enabled=true"
curl -X POST -H 'X-Test-Env: green' "http://<host>/scenario-runner/api/archive-throttling/reset"
# Other traffic runs (traffic only, a repeating cycle): see relibank/telemetry_loadgen/README.md in goblin-swarm
```
`toggle` also takes `retry_after` (0–60, default 2) and `share_503` (0–1, default 0.3).

**Throttling is never left on by the loadgen:** it switches it off when the run ends, fails or is cancelled,
and a last workflow step does it even if the script dies. If you ever need to do it yourself, call `reset`.

**Locally with skaffold:** `skaffold dev` from the repo root brings up the gateway and archive with the rest of
the app (see `k8s/overlays/dev/`). Source `skaffold.env` first. **Do not run it with an AKS context selected**:
the hooks in `skaffold.yaml` call plain `kubectl`. Pass `--kube-context docker-desktop`, or use a kubeconfig
that contains only the local cluster. Check it with
`kubectl -n relibank get deploy compliance-archive relibank-telemetry-gateway`.

## Look at it in New Relic

In the environment's own account:

- **Gateway entity:** APM & Services → **Services - OpenTelemetry** → `relibank-telemetry-gateway`. Three
  entities share that name (the collector, an eBPF-discovered service, the Kubernetes deployment); the
  collector is the one with the telemetry.
- **Archive entity:** the APM app named `... - Compliance Archive`.

```sql
-- Gateway receiver, per minute
SELECT sum(otelcol_receiver_accepted_log_records) AS received, sum(otelcol_receiver_refused_log_records) AS refused
FROM Metric WHERE service.name = 'relibank-telemetry-gateway' TIMESERIES 1 minute
-- Archive exporter, per minute
SELECT sum(otelcol_exporter_send_failed_log_records) AS failed, sum(otelcol_exporter_enqueue_failed_log_records) AS dropped,
       max(otelcol_exporter_queue_size) / max(otelcol_exporter_queue_capacity) * 100 AS saturation_pct
FROM Metric WHERE service.name = 'relibank-telemetry-gateway' AND exporter = 'otlphttp/archive' TIMESERIES 1 minute
-- Logs that reach New Relic (use message; log.type does not work as a facet)
SELECT count(*) FROM Log WHERE message IN ('audit event', 'other event') FACET message TIMESERIES 1 minute
-- Archive: the 429 / 503 mix
SELECT filter(count(*), WHERE status_code = 200) AS ok, filter(count(*), WHERE status_code = 429) AS r429,
       filter(count(*), WHERE status_code = 503) AS r503 FROM ArchiveIngestRequest TIMESERIES 1 minute
```
Queries accept explicit times too (`SINCE 1794472055 UNTIL 1794474900`, epoch seconds).

## Alerts

Created in the central **Demogorgon Alerts** account by `nr_alerts_telemetry_gateway.tf` and sent to
`#demogorgon-alerts` through a Slack workflow. Every name carries the environment, taken from the environment
you deploy (`var.demo_environment`), never hardcoded. Nothing is created unless the alerts account id, the alerts
key, the Slack destination and the Slack channel are all set for that environment.

| Condition | Fires when | Slack title |
|---|---|---|
| Archive Queue Saturation | queue at 95% or more for 5 minutes | Archive Queue Saturated \| `<env>` telemetry gateway |
| Queue Drops | any drops for 60 seconds | Audit Logs Dropped \| `<env>` telemetry gateway |
| Receiver Refusals | any refusals for 60 seconds | Incoming Logs Refused \| `<env>` telemetry gateway |
| Not Recovered | queue at 95% or more for 15 minutes | Not Recovering \| `<env>` telemetry gateway |

Policy name: `ReliBank (<env>) - Telemetry Gateway`. Apply or update them with **Deploy ReliBank NR** in
catapult-service.

## Tests

`tests/telemetry_gateway_validation/` is deliberately left out of the test-suite workflow's `all` option, which only
runs `tests/test_*.py`. Run it with the option `telemetry-gateway-validation`. A **local** `./run_tests.sh -t all`
does collect it (`pytest .`), and its scenario API tests then switch throttling on and off on whichever scenario
service `SCENARIO_SERVICE_URL` points at, so keep that on a local one.

| File | What it checks |
|---|---|
| `test_archive_throttling_scenarios.py` | Switch on, off, reset; state persists; bad values rejected; the chaos rate limiter is untouched |
| `test_compliance_archive.py` | 200 when off, a 429/503 mix when on, one `ArchiveIngestRequest` per request (runs in-process) |
| `test_otlp_ingest_auth.py` | `/otlp/` gives 401 without the token and 200 with it, also on the color route |
| `test_gateway_stage_logic.py` | Offline: every gateway check can both pass and fail, and names the stage and value |
| `test_gateway_telemetry.py` | Read-only New Relic check of the last run: healthy baseline, each failure stage by its deadline (+/- 2 min), recovery after the reset, and a negative control with throttling off |

Deadlines (minutes after switch-on): export failures over 50% by T+3; queue at 95% and drops by T+8; refusals
and a gap in New Relic logs by T+20; back to baseline within 8 minutes of the reset. "By" means at the latest,
so earlier passes.

Things to know when you run it:

- **It judges the last run the scenario service remembers**, read when the tests start. The scenario API tests in the
  same option switch throttling on and off, which **overwrites that memory** and would **end a run in progress**.
  Run the option once per real run, after the reset. To judge an older run, run
  `test_gateway_telemetry.py` by hand with `GATEWAY_RUN_START` and `GATEWAY_RUN_RESET` (epoch seconds, printed in the
  loadgen log).
- **The negative control** looks at the last 20 minutes (ending 2 minutes ago). It needs throttling to have been off
  for more than 23 minutes, with at least 5 minutes of logs flowing in that window. Right after a run it skips.
- It needs the environment's `NR_USER_API_KEY`, `NR_ACCOUNT_ID`, `BASE_URL` and `OTLP_INGEST_TOKEN`.

## Settings (names only)

| Where | Name | What |
|---|---|---|
| relibank GitHub environment | `NR_USER_API_KEY` (secret), `NR_ACCOUNT_ID`, `BASE_URL`, `OTLP_INGEST_TOKEN` (secret) | The test option |
| catapult-service | `RELIBANK_OTLP_INGEST_TOKEN` (secret) | The `/otlp/` token, passed to the blue/green proxies |
| catapult-service | `ALERTS_NR_ACCOUNT_ID`, `ALERTS_NR_REGION`, `ALERTS_NR_USER_API_KEY`, `ALERTS_SLACK_DESTINATION_ID`, `ALERTS_SLACK_CHANNEL_ID` | The alerts and the Slack route |
| goblin-swarm "Demogorgon `<Env>`" environment | `BASE_URL`, `OTLP_INGEST_TOKEN` (secret) | The loadgen |

## Rolling out to an environment

1. Build the images from the relibank branch (catapult **Build & Push ReliBank Container Images**), then
   **Deploy ReliBank App**. Check `GET /scenario-runner/api/archive-throttling/config` answers 200 (a 404 means
   the scenario-runner image is older than this feature: rebuild and restart the pod).
2. Set the settings above, then **Deploy ReliBank NR**.
3. Run the loadgen once (the ticket's run) and then the test option. Sandbox is done; staging and prod are next.
4. Before exposing `/otlp/` on staging or prod, put **TLS** in front of it. The sandbox host has no valid
   certificate, so the bearer token travels in clear text there.

## Known limits and open decisions

- **Order of events.** The ticket's story has refusals last (around T+20). Measured, refusals start at T+5, before
  the queue is full, and match the drops from T+6, because a full archive queue is refused at the receiver. The tests
  and alerts treat the ticket's times as deadlines, so they pass. Whether to reword the story or tune the gateway
  is a decision for the ticket owners.
- **429/503 are not APM errors.** The archive's status codes and events show the mix, but the APM error rate stays 0.
- **`X-Test-Env`.** The tests show the color route checks the token, not that the header picks the color.
- **Collector warning.** The gateway logs `"otlphttp" alias is deprecated` at start-up. Renaming the exporter changes
  the `exporter` value the alerts and tests use (see `otel_collector_gateway/CLAUDE.md`).

## Troubleshooting

| You see | Likely cause |
|---|---|
| Loadgen stops with "archive throttling is not available here (HTTP 404)" | That environment's scenario-runner image predates this feature. Rebuild and restart it |
| Loadgen stops with "already on" | Another run left throttling on. `reset` it first |
| Loadgen preflight 401 / 000 / 404, 502, 503 | Wrong token / host unreachable or TLS / proxy rule or gateway pod missing |
| Telemetry tests: "0 of 10 minutes received any logs" | They judged a leftover blip, not the real run (the scenario API tests overwrote it). Use `GATEWAY_RUN_START` / `GATEWAY_RUN_RESET` or do a new run |
| Telemetry tests skip with "throttling was on for 0.0 min" | Same cause |
| The exporter check fails | The `exporter` value differs; it lists what it found |

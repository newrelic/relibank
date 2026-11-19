# relibank-telemetry-gateway (OTel collector) — Context for Claude

The gateway collector. External producers send logs to `/otlp/` (token-gated, in the nginx proxies). The
gateway sends every log to New Relic, and the audit logs (`log.type == "audit"`) also to
[`compliance-archive`](../compliance_archive/CLAUDE.md). The `log.type` name is a placeholder until the producer
contract is settled (open item on NR-638736). Config is in `config.yaml`, pinned by digest in the `Dockerfile`.
**AKS runs a hand-synced copy** of that file in catapult-service
(`relibank_deployer/terraform/aks/app_module/templates/otel-collector-gateway-config.yaml`, same body with a
4-line header), so a change here does not reach AKS until the copy is updated too. Its own telemetry (the data
Collector Observability shows) comes from the shared `internal-telemetry-config` loaded as a second `--config`;
that file is not edited here.

> **Prime Directive:** See the [root `CLAUDE.md`](../CLAUDE.md). The gateway is where the backpressure
> shows up, but it is not the cause. Diagnose from New Relic telemetry, and don't *spontaneously* tune or
> "fix" the settings below during unrelated work. The remediation for this story lives in
> [`compliance_archive/CLAUDE.md`](../compliance_archive/CLAUDE.md) — use it as written.
>
> **Modes:** Investigation mode is the default. On the demo-engineering team, run **`/build-mode`**. See
> [root `CLAUDE.md`](../CLAUDE.md) → *Modes* and the runbook
> [`docs/TELEMETRY_PIPELINE_SCENARIO.md`](../docs/TELEMETRY_PIPELINE_SCENARIO.md).

---

## 🚨 Settings that are tuned on purpose (don't spontaneously "fix")

These values set the timing of the whole story, and the alert thresholds and tests are calibrated to them.
They were measured in the Phase 0 spike and two sandbox proof runs.

| Setting | Value | Why it matters |
|---|---|---|
| Archive exporter queue | 6000 items, 2 consumers, `block_on_overflow: false` | A full queue refuses new data right away instead of waiting. The queue reaches 95% about 6 minutes after the archive starts refusing. |
| Retry on the archive exporter | up to 180 s, honors `Retry-After` | Export failures are first counted when this window runs out, so it sets when the failures appear (about T+2 to T+3 minutes). The queue drops are a separate thing: they start when the queue is full. |
| No batch step on the archive path | — | A full archive queue becomes a refusal at the receiver, which also holds back the New Relic copy. |
| `memory_limiter` | 256 MiB limit, 64 MiB spike, checks every 1 s | Pod limit is 512Mi; the collector refuses data before the pod is killed. |
| Exporter ids | `otlphttp/archive` (and the New Relic one) | The alerts and `tests/telemetry_gateway_validation/` filter on the `exporter` attribute with this value. Renaming an exporter (for example to `otlp_http/...`, which the collector's deprecation warning suggests) changes that value: update the alerts and the tests in the same change. |

**Don't:** add a batch step, enlarge the queue, change the retry window or make the archive exporter
non-blocking "to make it more resilient". That removes the story. Don't treat the collector's
`"otlphttp" alias is deprecated` start-up warning as a bug to fix on its own.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/relibank-telemetry-gateway --tail=50 -f
kubectl -n relibank port-forward deploy/relibank-telemetry-gateway 13133:13133   # health_check extension
```
Health check: `http://localhost:13133/`. OTLP/HTTP is on 4318, gRPC on 4317.

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

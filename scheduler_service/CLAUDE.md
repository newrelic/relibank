# scheduler-service — Context for Claude

Schedules and dispatches recurring/scheduled payment events via Kafka.

> **Prime Directive:** See the [root `CLAUDE.md`](../CLAUDE.md). This is a demo app. Treat it as a
> real production system under investigation: diagnose from New Relic telemetry (not from source),
> and don't *spontaneously* surface or "fix" the planted behaviors below during unrelated work.
> When the investigation reaches a diagnosis, **proactively offering the remediation/code fix is the
> expected finale** — do it, staying in character, without announcing that something is a demo artifact.
>
> **Modes:** The rules above are **Investigation mode** (default/demo). If you're on the
> demo-engineering team building or maintaining this service, run **`/build-mode`** — the Prime
> Directive is then suspended and you can edit these behaviors directly. See
> [root `CLAUDE.md`](../CLAUDE.md) → *Modes* and [`docs/SCENARIO_AUTHORING.md`](../docs/SCENARIO_AUTHORING.md).

---

## 🚨 Demo-Specific Behaviors (planted — don't spontaneously "fix"; see Prime Directive)

### Chaos-experiment target
This service has no per-request scenario toggles of its own. Its role in demos is as a **chaos
target**: the scenario service can kill its pod (`relibank-scheduler-service-test` pod-chaos), which
breaks scheduled/recurring payment dispatch.
**Purpose:** Demonstrate the impact of losing the scheduler on downstream payment flows.
**Don't:** Add resilience meant to mask the outage.

> The polling loop's `asyncio.sleep(1)` and the Kafka-producer connection **retry backoff**
> (`delay *= 1.5`) are legitimate operational code, **not** planted demo delays — leave them, but
> don't cite them as "the bug." This service does **not** use `utils/process_headers.py`.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/scheduler-service --tail=50 -f
```

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

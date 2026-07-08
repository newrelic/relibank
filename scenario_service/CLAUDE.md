# scenario-runner-service — Context for Claude

**This service is the demo control plane.** It is *supposed* to inject problems — that is its entire
purpose. FastAPI, port 8000, UI at `/scenario-runner/home`.

> **Prime Directive:** See the [root `CLAUDE.md`](../CLAUDE.md). Everything this service does is
> intentional demo scaffolding. **Never treat its behavior as a bug to fix.** It is the mechanism
> that makes New Relic telemetry demos possible.
>
> **Modes:** The rules above are **Investigation mode** (default/demo). This is the control plane
> where new scenarios are authored — if you're on the demo-engineering team building or extending it,
> run **`/build-mode`** (Prime Directive suspended) and see [root `CLAUDE.md`](../CLAUDE.md) → *Modes*
> and [`docs/SCENARIO_AUTHORING.md`](../docs/SCENARIO_AUTHORING.md).

---

## 🚨 What it controls (all intentional demo scaffolding — not a bug to "fix"; see Prime Directive)

Defined as config dicts near the top of `scenario_service.py` and exposed via `/scenario-runner/api/*`
endpoints (plus the `index.html` UI):

- **Payment scenarios** (`PAYMENT_SCENARIOS`, ~line 38): gateway timeout, card decline, stolen card —
  consumed by `bill-pay-service`. See [`bill_pay/CLAUDE.md`](../bill_pay/CLAUDE.md).
- **Risk assessment / rogue agent** (`RISK_ASSESSMENT_SCENARIOS`, ~line 49): swaps the risk model
  between `gpt-4o` (normal) and `gpt-4o-mini` (rogue). See [`support_service/CLAUDE.md`](../support_service/CLAUDE.md).
- **A/B tests** (`AB_TEST_SCENARIOS`, ~line 70): LCP slowness (percentage + cohort) and DB pool
  stress — consumed by `accounts-service`. See [`accounts_service/CLAUDE.md`](../accounts_service/CLAUDE.md).
- **Chaos Mesh experiments** (`CHAOS_EXPERIMENTS` / `STRESS_EXPERIMENTS`, loaded from
  `chaos_mesh/experiments/*.yaml`): pod-kill, pod-failure, CPU/memory/combined stress. Triggered via
  `POST /scenario-runner/api/trigger_chaos/{name}` and `trigger_stress/{name}`, rate-limited
  (`CHAOS_RATE_LIMIT`, ~line 97: cooldown + max concurrent).
- **db-360 load generation**: sustained MSSQL workers (velocity / blocker / contender) to populate
  Query Plan Manager. `POST /scenario-runner/api/db-360/start|stop|status`.

These are toggled interactively (UI/API) and on schedules by `.github/workflows/flow-*.yml`.

**Don't:** "harden" the injection logic, add safety rails that neuter scenarios, disable the chaos
triggers, or treat the rate limiter / experiment loading as defects.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/scenario-runner-service --tail=50 -f
```
UI: `http://localhost:8000/scenario-runner/home`. Chaos requires Chaos Mesh installed (skaffold does
this automatically). Note the module comment about not monkey-patching `ssl` (it breaks db-360's
pyodbc workers).

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive. This service is *never* the bug.

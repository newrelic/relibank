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
- **Archive throttling** (`ARCHIVE_THROTTLING`, ~line 81; endpoints `GET .../archive-throttling/config`,
  `POST .../toggle`, `POST .../reset`, ~lines 1098–1150): makes `compliance-archive` answer 429/503 plus
  `Retry-After`, which backs up the telemetry gateway's archive queue. Settings: `retry_after` (0–60 s) and
  `share_503` (0–1); bad values return `{"status": "error"}` and change nothing. The state is **in memory**
  and keeps `enabled_at` / `reset_at` (epoch seconds, kept after a reset) as the start and end of the last
  run, which `tests/telemetry_gateway_validation/` reads. It has a "Telemetry Pipeline" card in `index.html`.
  It deliberately does **not** use `CHAOS_RATE_LIMIT`. See [`compliance_archive/CLAUDE.md`](../compliance_archive/CLAUDE.md)
  and [`docs/TELEMETRY_PIPELINE_SCENARIO.md`](../docs/TELEMETRY_PIPELINE_SCENARIO.md).
- **Chaos Mesh experiments** (`CHAOS_EXPERIMENTS` / `STRESS_EXPERIMENTS`, loaded from
  `chaos_mesh/experiments/*.yaml`): pod-kill, pod-failure, CPU/memory/combined stress. Each YAML's
  `namespace: relibank` is overridden at startup with the pod's actual namespace (`get_current_namespace()`),
  so experiments still target the right pods on blue/green (`relibank-blue`/`relibank-green`).
  Triggered via `POST /scenario-runner/api/trigger_chaos/{name}` and `trigger_stress/{name}`,
  rate-limited (`CHAOS_RATE_LIMIT`, ~line 97: cooldown + max concurrent). Both accept `?dry_run=true`
  to report `matched_pods` for the experiment's selector without creating a chaos-mesh resource or
  touching the rate limiter — an opt-in read that doesn't change default trigger behavior, used by
  `tests/test_scenario_service.py::test_all_chaos_scenarios_have_matching_pods` to catch
  selector/namespace drift in CI.
- **DB Performance Matrix acts 3-4** (`/scenario-runner/api/db-matrix/{competing-query|plan-regression}/start|stop|status`,
  plus `GET /db-matrix/status` and `POST /db-matrix/reset`). Time-boxed runner-side SQL against MSSQL: an unindexed analytics
  scan joining `BankTransactions`/`Merchants` (max 5 min), and `IX_BankTxn_Account` dropped with an account-lookup driver
  (default 7 min, max 10 min). One at a time, never alongside db-360. The index is always recreated on stop, expiry, and
  shutdown; `reset` recreates it even when nothing is running (recovery if the pod was killed mid-run). `plan-regression`
  retries the `DROP INDEX` (5 s lock timeout per attempt, every ~3 s) until its window ends, because other queries scanning
  `BankTransactions` can hold the schema lock; check `stats.index_dropped`, `drop_attempts`, `drop_lock_timeouts` in status
  (never dropped = nothing ran). It first runs the lookup once a second for up to 150 s (New Relic's top-query collector
  reports 60 s deltas, so the plan needs two scrapes) with the index in place, so monitoring records the index-seek plan
  before the drop and shows the later scan as a plan-hash change (`stats.phase`: baseline, dropping, regression;
  `baseline_iterations`). Act 2 (Ledger lock-contention) and act 1 (network/DNS chaos) are tracked on other tickets and are
  not part of this service yet. Both scenarios also run an orphan-session guard before start and after stop/expiry/exception
  (`_dbmatrix_clear_orphan_sessions`, `DBMATRIX_ORPHAN_WAIT_THRESHOLD_SECONDS = 300`): it `KILL`s any session stuck in
  `ASYNC_NETWORK_IO` for 5+ minutes while holding an `OBJECT` lock on `BankTransactions`/`Merchants` — the exact profile
  behind 3 real incidents where an unrelated leaked session silently blocked every `DROP INDEX` retry for the whole run —
  and records what it found/killed in `preflight_orphan_check`/`postflight_orphan_check` in `/status`. `/db-matrix/reset`
  runs the same clear before restoring the index. Detection query notes, both confirmed live against real stuck sessions
  in sandbox: `sys.dm_exec_requests.wait_time` is the *current* wait instance's duration, not the request's total age — it
  cycles in the 100-2000ms range even for a session stuck over an hour, so the threshold check uses `start_time` instead.
  And `OBJECT_NAME(resource_associated_entity_id)` isn't safe inside the `WHERE` clause even with a `resource_type =
  'OBJECT'` filter alongside it — SQL Server doesn't guarantee that filter runs first, so the function still gets called
  on PAGE/KEY rows whose id is a hobt_id too large for `OBJECT_NAME`'s int parameter, raising an arithmetic-overflow
  error; comparing against `OBJECT_ID('dbo.BankTransactions')`/`OBJECT_ID('dbo.Merchants')` directly avoids it.
- **db-360 load generation**: sustained MSSQL workers (velocity / blocker / contender) to populate
  Query Plan Manager. `POST /scenario-runner/api/db-360/start|stop|status`.

These are toggled interactively (UI/API) and on schedules by `.github/workflows/flow-*.yml`.

**Don't:** "harden" the injection logic, add safety rails that neuter scenarios, disable the chaos
triggers, or treat the rate limiter / experiment loading as defects. `dry_run` is opt-in and only
reports pod counts — it must never become the default or gate the real trigger path. Don't put the
archive-throttling switch behind the chaos rate limiter, and don't make it persist across a restart
(a restart switching it off is the safe default). The orphan-session guard is scoped tightly to the
exact `ASYNC_NETWORK_IO` + `OBJECT`-lock-on-`BankTransactions`/`Merchants` profile from real incidents —
don't widen its filters to other wait types or tables, and never point it at db-360's own blocker
(an intentional exclusivity mechanism, not a leak).

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

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

> `run_spending_velocity_sample()` and `run_ledger_rebuild_sample()` (every 5 minutes, alongside
> `check_for_due_payments()`'s every-1-minute poll) exist purely to keep
> `sp_CalculateSpendingVelocity`/`sp_RebuildAccountLedgerBalance` showing continuous activity in
> New Relic's QPM panels — real operational code, not a planted behavior.
>
> **Why `@Months=6` and `fetchmany()`, not `3` and `fetchall()`:** New Relic's wait-time-by-category
> chart (`DbServerQuerySample`) only gets data when NRDOT's DMV poll happens to land while a query
> is still executing. At `@Months=3` the query finished in ~4s and the poll essentially never
> caught it, so the chart stayed empty on every environment except sandbox (which got incidental,
> unrelated traffic to this procedure). At `@Months=6` it runs ~10s, scanning the full 2M-row
> `BankTransactions` table — long enough to be caught reliably. That query also returns ~460K rows,
> and `cursor.fetchall()` buffers the entire result in process memory at once (measured ~745MB
> peak) — well past this service's 256Mi container limit, which OOM-killed the pod every ~5
> minutes the first time this shipped. Draining with `fetchmany()` in 2000-row batches keeps peak
> memory flat (~27MB measured) regardless of `@Months`, with no change to the server-side
> suspended/`ASYNC_NETWORK_IO` wait state NRDOT's poll actually keys off — confirmed live via
> `sys.dm_exec_requests` mid-execution. No `@Months` value above `3` fits in 256Mi with
> `fetchall()`, so this needed the `fetchmany()` fix, not a smaller parameter.
> `run_ledger_rebuild_sample()` got the same `fetchmany()` loop preemptively — `Transactions` is
> small today so it's a no-op there now, but it would hit the identical OOM the moment that
> table's row count grows.

---

## Connection resilience

`get_db_connection()`/the shared `db_connection` global had three gaps fixed alongside NR-654694
(relibank's `scenario_service` orphan-session guard): no connect timeout, no reconnect-on-failure
(a broken connection stayed in the global forever and kept getting reused), and the three
scheduled jobs called pyodbc synchronously inside `async def`, blocking the whole event loop for
each query's duration. Fixed: `pyodbc.connect(..., timeout=10)`; `_reset_db_connection()` closes
and clears the global on any exception so the next scheduled run reconnects fresh; each job's DB
work now runs via `asyncio.to_thread(...)`. This is the same `ASYNC_NETWORK_IO` wait state noted
above for `sp_CalculateSpendingVelocity` — a stale/half-drained connection left over from an
interrupted run here is a plausible root cause of the orphaned sessions NR-654694 guards against
symptomatically in `scenario_service`. `_db_connection_lock` exists because `run_spending_velocity_sample`
and `run_ledger_rebuild_sample` share the same 5-minute tick, and `asyncio.to_thread` means their DB work
can now genuinely run on two threads at once — pyodbc connections aren't safe for concurrent use, so
every access to `db_connection` is serialized through the lock.

## Local dev / debug

```bash
kubectl logs -n relibank deployment/scheduler-service --tail=50 -f
```

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

# transaction-service — Context for Claude

Processes and retrieves payment transactions; Kafka consumer for payment events. FastAPI + MSSQL,
port 5001.

> **Prime Directive:** See the [root `CLAUDE.md`](../CLAUDE.md). This is a demo app. Treat it as a
> real production system under investigation: diagnose from New Relic telemetry (not from source),
> and don't *spontaneously* surface or "fix" the planted behaviors below during unrelated work.
> When the investigation reaches a diagnosis, **proactively offering the remediation/code fix is the
> expected finale** — do it, staying in character, without announcing that something is a demo artifact.

---

## 🚨 Demo-Specific Behaviors (planted — don't spontaneously "fix"; see Prime Directive)

### 1. Blocking / lock-contention endpoint
**Location:** `transaction_service.py` — `GET /transaction-service/blocking` (~line 835).

Opens a transaction, takes `UPDLOCK, ROWLOCK, HOLDLOCK` on a batch of high-risk flagged rows in
`BankTransactions`, then holds it with `WAITFOR DELAY '<delay_seconds>'` (~line 900) before
committing. Concurrent queries block on the held locks.
**Purpose:** SQL Server lock/blocking contention with rich multi-operator query plans, surfaced via
NRDOT MSSQL monitoring / Query Plan Manager.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Remove the long-held exclusive lock so concurrent transactions stop blocking."
- *Internal (do not surface):* `transaction_service.py` → `create_blocking_scenario()`
  (~lines 861–900) — drop the `WITH (UPDLOCK, ROWLOCK, HOLDLOCK)` hints and the `WAITFOR DELAY` hold
  (or short-circuit the endpoint).

### 2. Slow query generator
**Location:** `transaction_service.py` — `generate_slow_query(...)` (~line 1027) and related
`slow_query` load path.

Runs deliberately expensive queries (e.g. window functions over ~500K rows) to add CPU/DB load.
**Purpose:** Slow-query and CPU telemetry, and populating query-plan panels.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Bound the analytical query cost."
- *Internal (do not surface):* `transaction_service.py` → `generate_slow_query()` (~line 1027) —
  remove `OPTION (MAXDOP 1)` (allow parallelism) and narrow the date window (months → last day) so the
  scan is bounded (or short-circuit the endpoint).

### 3. Resource limits (k8s)
`k8s/base/services/transaction-service-deployment.yaml` sets a **CPU limit with no memory limit**,
and MSSQL is intentionally memory-constrained (`k8s/base/databases/mssql-deployment.yaml`) so heavy
queries can queue on `RESOURCE_SEMAPHORE`. These constraints are deliberate demo setup — don't
"right-size" them.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Right-size database and service memory so heavy queries stop queuing on
  `RESOURCE_SEMAPHORE`."
- *Internal (do not surface):* raise `MSSQL_MEMORY_LIMIT_MB` / the memory limit in
  `k8s/base/databases/mssql-deployment.yaml`, and add a memory limit in
  `k8s/base/services/transaction-service-deployment.yaml`.

### 4. Shared request-header hooks
Calls `process_headers(...)` from [`utils/process_headers.py`](../utils/process_headers.py):
blocking `time.sleep` (`extra-transaction-time` header) and HTTP error injection (`error` header).
Intentional — see root `CLAUDE.md`.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/transaction-service --tail=50 -f
```
`transaction-service` is a primary chaos-experiment target (pod-kill, CPU/combined stress). See
`transaction_service/notes.md` and the demo load generators in `demo_flows/stress_loadgen/`.

> Skaffold file-sync sometimes misses Python changes here — try `kubectl rollout restart` or force a
> Dockerfile rebuild (see `frontend_service/CLAUDE.md` → "Skaffold File Sync Limitations").

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

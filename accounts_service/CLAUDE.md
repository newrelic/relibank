# accounts-service — Context for Claude

Manages user accounts and balances. FastAPI + PostgreSQL, port 5002.

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

### 1. Database connection-pool stress
**Location:** `accounts_service.py` — `assign_user_to_pool()` (~line 72),
`get_db_connection_with_pool_tracking()` (~line 132), custom attrs (~line 352).

Users are deterministically assigned to `pool-a`/`pool-b` via an MD5 hash of their id (~50/50).
When the scenario is enabled, connections for the affected pool are **held for a configured delay**
(`db_pool_stress_delay_ms`), simulating pool contention/exhaustion. Emits `db.pool_id`,
`db.pool_wait_time_ms`, `db.pool_exhausted` custom attributes.

**Trigger:** scenario-service `POST /scenario-runner/api/ab-testing/db-pool-stress`.
**Purpose:** Performance degradation isolated to ~half of users sharing infrastructure — a
"some users are slow" investigation. Full runbook: [docs/DATABASE_POOL_SCENARIO.md](../docs/DATABASE_POOL_SCENARIO.md).
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Release pooled DB connections immediately instead of holding them, so one
  cohort stops starving the shared pool."
- *Internal (do not surface):* `accounts_service.py` → `get_db_connection_with_pool_tracking()`
  (~line 171) — remove the `await asyncio.sleep(delay_ms / 1000.0)` connection hold. (A complementary
  capacity fix: raise the pool max from `SimpleConnectionPool(1, 10, …)`, ~line 240. Operational
  equivalent: disable the `db-pool-stress` scenario.)

### 2. LCP slowness A/B test
**Location:** `accounts_service.py` — `LCP_SLOW_USERS` set (~line 99) and the LCP branches
(~lines 685 and 730).

Injects an artificial delay reported to the browser (`lcp_delay_ms`) either for a **percentage**
of all users (`lcp_slowness_percentage_*`) or for a **hardcoded cohort** of test users
(`lcp_slowness_cohort_*`), tagging them `custom.lcp_treatment = "slow"`.

**Trigger:** scenario-service `ab-testing` endpoints. The frontend applies the delay on render (see
[`frontend_service/CLAUDE.md`](../frontend_service/CLAUDE.md)).
**Purpose:** Real-user-monitoring (Core Web Vitals / LCP) A/B story with a clean treatment split.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Stop the accounts API from returning a render-delay directive to the browser so
  LCP reflects real page-load time."
- *Internal (do not surface):* `accounts_service.py`, browser-user endpoint (~lines 685 & 730) — drop
  the `lcp_slowness_percentage_*` / `lcp_slowness_cohort_*` branches and always return
  `lcp_delay_ms: 0`. Pair with the frontend edit in
  [`frontend_service/CLAUDE.md`](../frontend_service/CLAUDE.md) (remove the client-side delay).
  (Operational equivalent: disable the `ab-testing` LCP scenarios.)

### 3. Shared request-header hooks
Calls `process_headers(...)` from [`utils/process_headers.py`](../utils/process_headers.py): a
**blocking `time.sleep`** (`extra-transaction-time` header) and HTTP error injection (`error`
header). Intentional — see root `CLAUDE.md`.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/accounts-service --tail=50 -f
```
Toggle scenarios via the scenario UI/API, not by editing code.

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

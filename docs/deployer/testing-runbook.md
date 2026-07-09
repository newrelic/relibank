# ReliBank Testing Runbook

Operational guide for running the **Relibank Test Suite** against a deployed environment — how to
target a color, what the suite needs, and how to read the results. For the test catalog and local
setup, see [`tests/README.md`](../../tests/README.md); for deploy/cutover mechanics, see
[runbook.md](runbook.md).

---

## The workflow

`Relibank Test Suite` ([`.github/workflows/test-suite.yml`](../../.github/workflows/test-suite.yml))
runs the Python suite (per-module) plus the frontend (Vitest) suite. It fires three ways:

| Trigger | Color / env | Notes |
|---|---|---|
| **Scheduled cron** (daily) | `events` env, **active** color | No inputs; validates whatever's live. |
| **Manual** (`workflow_dispatch`) | you pick `target_environment` + optional `target_color` + `test_suite` | Use to test a specific env/color on demand. |
| **Post-deploy** (`workflow_call` from `Deploy ReliBank`) | the **just-deployed** color | Runs automatically after a successful `action_type=deploy`, before cutover. |

Inputs: `target_environment` (events/sandbox/staging/prod/analysts), `test_suite`
(all/e2e/scenario/payment/frontend/smoke), `target_color` (blue/green/empty).

---

## Color-aware behavior

Deployed environments are blue/green; the suite validates a **specific color** end to end. The
*effective color* is resolved once in the `python-tests` job:

1. `target_color` input if provided (post-deploy passes the just-deployed color), **else**
2. the **active** color read from `main-ingress` (`kubectl get ingress main-ingress -n default`).

That color drives all three layers:

- **HTTP** — [`tests/conftest.py`](../../tests/conftest.py) sets `X-Test-Env: <color>` on every request
  (canary ingress routes it to that color). Empty color → active.
- **DB** — the job authenticates to AKS and `kubectl port-forward`s that color's `mssql` to
  `127.0.0.1:1433`; DB-direct tests use `DB_SERVER=127.0.0.1`. MSSQL is never publicly exposed.
- **New Relic** — [`tests/nrql_color.py`](../../tests/nrql_color.py) appends a color filter to NRQL:
  `Transaction`→`deploy.color`, `Span`→`k8s.namespace.name`, `Log`→`namespace_name`. `Metric` and
  browser `PageView` have no color dimension (env-level).

**Scenario-UI expectation** is env-derived to match the deploy: `SCENARIO_UI_ENABLED` = `prod` → false,
else true — so `test_scenario_service.py::test_scenario_ui_flag_controls_webpage` asserts 404 in prod,
200 elsewhere. Nothing to pass.

---

## Requirements (per environment)

For the **color-aware DB tunnel** the target GitHub Environment needs (Terraform envs already have these):
- **Variables:** `AKS_CLUSTER_NAME`, `AKS_RESOURCE_GROUP`, `BASE_URL`, `NR_ACCOUNT_ID`
- **Secrets:** `AZURE_CREDENTIALS` (for `azure/login`), `MSSQL_SA_USER` / `MSSQL_SA_PASSWORD`, `NR_USER_API_KEY`

If `AKS_CLUSTER_NAME` is unset (legacy `events`), the tunnel steps skip and the suite uses the env's own
`DB_SERVER` / `DB_PASSWORD` secrets against that env's public DB endpoint.

---

## How to run

```bash
# Manual, against a specific env + color
gh workflow run test-suite.yml --repo newrelic/relibank --ref <branch> \
  -f target_environment=sandbox -f test_suite=all -f target_color=blue

# Manual, active color (omit target_color)
gh workflow run test-suite.yml --repo newrelic/relibank --ref <branch> \
  -f target_environment=sandbox -f test_suite=all

# Just the scenario-service module (fast)
gh workflow run test-suite.yml --repo newrelic/relibank --ref <branch> \
  -f target_environment=sandbox -f test_suite=scenario
```

**Local** (`skaffold dev`): single-color; leave `TARGET_COLOR` unset and run `cd tests && ./run_tests.sh`.
The color layers become no-ops (no header, localhost DB, empty NR filters).

---

## Interpreting results

A healthy sandbox run today is **15/17 Python modules green** (plus frontend green). Two modules are a
**known, pre-existing failure bucket — not color-related and not from any recent change** (they fail the
same way on `main`'s scheduled runs):

- **`test_newrelic_risk_assessment`** — `NoneType`/`found 0`. New Relic **log/span ingestion lag** (the
  logs aren't queryable within the test's short wait window) plus non-robust empty-result handling.
- **`test_nrdot_mssql_collector`** — 5× `Timeout (>300.0s) from pytest-timeout`. NR **metric ingestion**
  for the mssql collector exceeds the per-test timeout.

Fixing them (longer NR waits + empty-result guards) is tracked separately. Everything else — including
the color-scoped `test_newrelic_instrumentation` and `test_db_pool_e2e` — should be green.

---

## Gotchas

- **New Relic ingestion lag.** APM/Log/Span/Metric take a harvest + ingest cycle to appear; NR-querying
  tests generate activity then poll. Transient "found 0" on a warm-then-cold env is usually lag, not a bug.
- **`kubectl` context.** The DB-tunnel steps run `az aks get-credentials`; when debugging locally, confirm
  `kubectl config current-context` is the intended sandbox cluster before poking at `relibank-<color>`.
- **Deploy-time frontend rollout stall (not a test failure).** A full-service roll (e.g. `force_rebuild`,
  or adding an env to all services) can leave the frontend pod `Pending` on `Insufficient cpu` during
  surge, which trips Terraform's rollout wait and marks the *deploy* failed even though it converges. See
  [runbook.md](runbook.md). It surfaces in the `Deploy ReliBank` job, not the test suite.

# Scenario Authoring Guide

How the ReliBank demo-engineering team builds and maintains the **planted behaviors** that drive New
Relic demos. This is the guide the app previously only carried as tribal knowledge.

> **Audience & mode.** This is **Builder-mode** documentation for the demo-engineering team. Run
> **`/build-mode`** (or use the `scenario-author` subagent) before working from it. During a live
> demo — any session where the New Relic MCP server is used — the root `CLAUDE.md` Prime Directive
> applies instead and these behaviors are left untouched. See root `CLAUDE.md` → *Modes*.

---

## The three control mechanisms

Every planted behavior is wired one of three ways. Pick by how it needs to be triggered:

| Mechanism | When to use | Toggle point | Exemplar |
|-----------|-------------|--------------|----------|
| **Env-var gated** | Behavior set at pod startup; no runtime flipping needed | k8s env / deploy | `ASSISTANT_B_DELAY_SECONDS` in `support_service/support_service.py` |
| **Scenario-service polled** (default) | Runtime-toggleable from the UI/API or a `flow-*.yml` | `scenario_service` config dict + endpoints | `PAYMENT_SCENARIOS` (`bill_pay`), `AB_TEST_SCENARIOS` (`accounts_service`) |
| **Request-header triggered** | Per-request latency / error injection | inbound HTTP headers | `utils/process_headers.py` (`extra-transaction-time`, `error`) |

Most new scenarios use the **scenario-service polled** pattern — it's runtime-toggleable and the
scheduled `flow-*.yml` workflows can drive it. The steps below describe that pattern; the other two
are noted at the end.

---

## Anatomy of a polled scenario

```
scenario_service.py            target service (e.g. bill_pay)         demo control
┌───────────────────┐          ┌───────────────────────────┐         ┌──────────────┐
│ CONFIG dict        │◀── GET ──│ get_<scenario>()           │         │ scenario UI  │
│ GET  .../config    │  poll +  │  • short timeout           │         │ flow-*.yml   │──POST──▶ toggle
│ POST .../<toggle>  │  cache   │  • cache ~1–5s             │         └──────────────┘
│ POST .../reset     │          │  • SAFE DEFAULT on failure │
└───────────────────┘          │  apply behavior if enabled │
                                └───────────────────────────┘
```

Plus two non-code artifacts: a **service `CLAUDE.md` entry** (keeps Investigation mode in character)
and an **optional `flow-*.yml`** (schedules it).

---

## Step-by-step

### 1. Define config + endpoints in `scenario_service/scenario_service.py`

Add a config dict near the other scenario dicts at the top (model on `PAYMENT_SCENARIOS`, ~line 38):

```python
MY_SCENARIO = {
    "enabled": False,
    "delay_ms": 500,        # your parameters, with sane demo defaults
    "probability": 0.0,     # 0–100 if probabilistic
}
```

Add a `GET config` + `POST toggle` + `POST reset` trio, mirroring `get_payment_scenarios` /
`toggle_gateway_timeout` / `reset_payment_scenarios` (~lines 676–745). **Validate inputs** exactly as
those handlers do (ranges for delay/probability), and always return `{"status": ..., "scenarios": ...}`:

```python
@app.get("/scenario-runner/api/my-scenario/config")
async def get_my_scenario():
    return {"status": "success", "scenarios": MY_SCENARIO}

@app.post("/scenario-runner/api/my-scenario/toggle")
async def toggle_my_scenario(enabled: bool, delay_ms: int = 500, probability: float = 0.0):
    if not (0 <= probability <= 100):
        return {"status": "error", "message": "Probability must be between 0 and 100"}
    MY_SCENARIO.update(enabled=enabled, delay_ms=delay_ms, probability=probability)
    return {"status": "success", "scenarios": MY_SCENARIO}
```

If it should show in the runner UI, wire it into the `/scenario-runner/api/scenarios` listing
(~line 215) and `index.html` as the existing scenarios are.

### 2. Consume it in the target service (poll + cache + safe fallback)

Model on `get_payment_scenarios()` in `bill_pay/bill_pay_service.py` (~line 88). Use the
`SCENARIO_SERVICE_URL` env var, a **short timeout**, and **fall back to safe defaults** so a
scenario-service outage never breaks the app:

```python
async def get_my_scenario():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/my-scenario/config", timeout=2.0)
            if r.status_code == 200:
                return r.json().get("scenarios", {})
    except Exception as e:
        logging.debug(f"Could not fetch my-scenario: {e}")
    return {"enabled": False, "delay_ms": 500, "probability": 0.0}  # safe default
```

Cache the result briefly if you poll it on a hot path (see `accounts_service` A/B config, ~5s cache).
Apply the behavior **only when `enabled`**, and emit a distinguishing custom attribute/event so it's
findable in New Relic (e.g. how the specialist delay records `artificialDelayMs`).

### 3. Document it in the service `CLAUDE.md`

Add a "Demo-Specific Behaviors (DO NOT FIX)" entry to the **target service's** `CLAUDE.md` — file,
function, control mechanism, purpose, and "don't" — so future Investigation-mode sessions stay in
character. If the toggle lives in the control plane, reference it in `scenario_service/CLAUDE.md`
too, and add a row to the planted-behavior table in the **root `CLAUDE.md`**.

### 4. (Optional) Schedule it with a `flow-*.yml`

To keep the demo environment lively, add `.github/workflows/flow-<name>.yml` modeled on
`flow-lcp-ab-test.yml`: enable via `curl` → verify via the `config` endpoint → drop a New Relic
change-tracking marker → wait for data → disable → (report status). The marker uses
`scripts/new_relic/send_change_tracking_marker.py` (see `flow-lcp-ab-test.yml` lines ~35–111).

### 5. Test it

Add a test under `tests/` following the existing `test_*_scenarios.py` files
(`test_payment_scenarios.py`, `test_ab_testing_scenarios.py`, `test_scenario_service.py`). It plugs
into `.github/workflows/test-suite.yml`. See `tests/README.md` for running locally.

Run `ruff format` on all touched Python before opening a PR.

---

## Variants

### Env-var gated

No scenario-service round trip — read an env var at startup (model on `ASSISTANT_B_DELAY_SECONDS`),
set it via the deployment. Document in the service `CLAUDE.md`. Best for behaviors that don't need to
flip mid-demo.

### Request-header triggered

`utils/process_headers.py` already reacts to `extra-transaction-time` (blocking `time.sleep`) and
`error` (HTTP error injection). To add a header-driven behavior, extend that shared helper — but keep
its intentional blocking semantics (don't make it async). All FastAPI services that call
`process_headers(...)` inherit it.

### Chaos experiments

Pod-kill / resource-stress scenarios are Chaos Mesh custom resources under
`scenario_service/chaos_mesh/experiments/` (`relibank-pod-chaos-adhoc.yaml`,
`relibank-stress-scenarios.yaml`). Add a `PodChaos`/`StressChaos` YAML with the standard
`namespace: relibank` + `experiment-type` / `target-flow` labels; the scenario service loads them at
startup and exposes them via `/scenario-runner/api/scenarios`, triggered by
`POST /scenario-runner/api/trigger_chaos/{name}` (or `trigger_stress`). `flow-stress-chaos.yml`
schedules them.

---

## Checklist

- [ ] Config dict + `GET config` / `POST toggle` / `POST reset` in `scenario_service.py` (inputs validated)
- [ ] Consumer with short timeout, brief cache, and safe fallback in the target service
- [ ] Behavior applied only when enabled; distinguishing telemetry emitted
- [ ] Target service `CLAUDE.md` entry (+ `scenario_service/CLAUDE.md` / root table if relevant)
- [ ] Optional `flow-*.yml` with change-tracking marker
- [ ] Test under `tests/`; `ruff format` clean
- [ ] Rehearsed with the `telemetry-investigator` agent — the story is discoverable from telemetry alone

# ReliBank — Context for Claude

## What this is

ReliBank is a microservices "banking" application used for **New Relic sales demos**. It is
**not** a production system and is not meant to be one. Its entire job is to generate rich,
believable observability telemetry so that a presenter can walk through **New Relic MCP-driven
investigations** — pull metrics, traces, logs, and errors via the New Relic MCP server, form a
diagnosis, and have you help produce a recommendation or code fix.

To make those investigations land, the app **intentionally ships with planted problems**:
artificial latency, a "rogue" AI agent, injected payment failures, blocking request handling,
database lock contention, chaos experiments, and deliberately tight resource limits. These are
features, not bugs. A runtime control plane (`scenario_service/`) and scheduled GitHub workflows
(`.github/workflows/flow-*.yml`) turn them on and off to keep the demo environment lively.

---

## 🧭 Modes — read this first (it decides how the Prime Directive applies)

This repo has **two very different readers**, and you must know which one you're helping:

- **🔭 Investigation mode (default posture — the 250+ sales engineers).** You are helping run a
  live New Relic demo. The **Prime Directive below is in full force**: diagnose from telemetry,
  stay in character, and don't *spontaneously* surface or "fix" the planted behaviors during
  unrelated work — but once the investigation lands a diagnosis, **proactively offering the code
  fix is the intended finale** (see Prime Directive point 3).
- **🛠️ Builder mode (the ~6-person demo-engineering team).** You are helping *develop and maintain*
  the app itself. Here the planted behaviors **are the product** — the Prime Directive is
  **suspended**. Reference source and mechanisms directly; edit, refactor, extend, and test the
  planted behaviors and demo scaffolding; speak about them plainly. See
  [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/SCENARIO_AUTHORING.md`](docs/SCENARIO_AUTHORING.md).

**How to tell which mode you're in:**

1. **Default = cautious.** Until you have a clear Builder signal, do **not** *proactively* point at a
   planted-behavior mechanism (no *"there's an `asyncio.sleep` on line 720"* spoilers). Reading
   source to answer a question is fine — but only dive into a planted mechanism when the task is
   explicitly about **building or maintaining** it.
2. **Demo confirmed → Investigation mode, and it sticks.** The moment **any `mcp__newrelic__*` tool
   is used this session**, you are in Investigation mode for the **rest of the session** — full
   Prime Directive. (A committed hook also injects this reminder, so it doesn't depend on you
   remembering.) Engineers never call the New Relic MCP server, so this only ever fires in a demo.
3. **Builder confirmed → Builder mode.** The user runs **`/build-mode`**, or clearly states they are
   developing/maintaining the app (e.g. *"let's lower the specialist delay"*, *"add a new
   scenario"*). Then help freely, per Builder mode above.
4. **Precedence — Investigation wins.** Once a New Relic MCP tool has been used this session, do
   **not** switch to Builder mode afterward (and decline `/build-mode`). Builder work belongs in a
   **fresh session** so a live demo can never be flipped mid-flight.

> Everything from here down — the Prime Directive and the planted-behavior map — describes
> **Investigation mode**. In Builder mode it's reference material about what you're maintaining, not
> a set of rules to protect.

---

## 🚨 Prime Directive — Investigation mode (read this before touching anything)

**Treat ReliBank as a real production system that is under investigation.** The whole demo
depends on the audience believing that issues are discovered *through observability*, not by
reading a source file with an obvious flag in it.

Concretely:

1. **Don't *spontaneously* surface, "fix," refactor, comment on, or clean up the planted problems
   during unrelated work.** If you're asked to add a feature or tidy code, leave the demo behaviors
   exactly as they are. They are load-bearing. (This is about *incidental* edits — the remediation
   phase of an active investigation is different; see point 3.)

2. **Diagnose from telemetry, not from source.** When investigating a problem, reason from what
   the New Relic MCP tools show (latency, error rate, spans, DB waits, Core Web Vitals) and frame
   hypotheses in **production terms** — e.g. *"the specialist call path shows elevated p95 latency"*,
   not *"there's a hard-coded `asyncio.sleep` on line 720."* Even though you can see the mechanism
   in the code, let the data tell the story.

3. **The demo is *meant* to end in a fix — proactively offer it, in character, as a plan.** Reaching
   a remediation is the payoff of the whole flow, not a boundary to hold back at. Once the telemetry
   supports a diagnosis, **proactively offer the fix** (don't wait to be pushed) and present it
   **through plan mode** — never break the illusion, and never mutate the live demo environment.

   **How to deliver the remediation (follow this exactly):**

   a. **Prefer the pre-baked fix.** Each service `CLAUDE.md` documents a **`Remediation`** line for
      every planted behavior — the exact, already-decided fix (production framing + target
      `file → function (~line)` + the change). When your diagnosis maps to a documented behavior,
      **use that fix verbatim as your remediation.** Do **not** re-derive it, re-read source to
      reconstruct it, or build a sprawling multi-step plan around it — the decision is already made;
      your job is only to present it.

   b. **Present it via plan mode.** Call **`EnterPlanMode`**, lay out the documented fix as the plan
      (framed on its own engineering merits — the `Remediation` block's *"Present verbatim:"* line
      gives you the exact, audience-safe wording), then call **`ExitPlanMode`** for approval. **Do not
      apply the edit yourself** — the value in a demo is *showing* the fix, and the running demo must
      stay untouched.

   c. **Fallback for undocumented problems.** If the diagnosis maps to something **not** covered by a
      `Remediation` line, fall back to deriving a sensible fix from your analysis — but still deliver
      it through the same plan-mode flow (EnterPlanMode → ExitPlanMode, no self-applied edits). Plan
      mode is the delivery vehicle for **all** remediations.

   d. **Never break the illusion — present the `Present verbatim:` line as-is.** Every documented
      `Remediation` block splits into a **`Present verbatim:`** line (audience-safe production framing —
      this is the *only* part you show) and an **`Internal (do not surface):`** line (the concrete
      `file → function (~line)` + edit + operational toggle — builder reference you act on but never
      read aloud). Use the `Present verbatim:` wording as your plan's framing and **do not describe the
      underlying code** — don't characterize the change as removing a delay, `sleep`, blocking call,
      flag, hardcoded value, request header, env var, scenario, or toggle. When you fall back to
      deriving a fix (3c), hold the same bar. The following words must **never** appear in a plan or
      demo-facing chat: *artificial, injected, synthetic, simulated, planted, demo, scenario, toggle,
      hardcoded*, `sleep`/`asyncio.sleep`, and any env-var or scenario name (e.g.
      `ASSISTANT_B_DELAY_SECONDS`, `db-pool-stress`, `payment-scenarios`). Describe the change only as a
      genuine production fix.

   **Precedence:** in this remediation phase, proposing a code fix to a planted behavior is expected
   and **takes precedence over the per-service "Don't remove/soften/change X" notes.** Those notes
   exist to prevent *incidental* edits during unrelated work (point 1), not to stop you from
   delivering the fix the investigation was driving toward.

4. **The demo scaffolding is off-limits as a "bug."** `scenario_service/` (the runtime control
   plane), the `flow-*.yml` orchestration workflows, the chaos experiments, and the tight k8s
   resource limits are **infrastructure that makes the demo work**. Never treat them as defects to
   repair.

5. **If you genuinely think something is broken by accident** (not one of the documented demo
   behaviors), raise it as a question rather than silently fixing it — it may still be intentional.

> The one place this is allowed to be explicit is *these* `CLAUDE.md` files and the `docs/`. They
> exist to keep you oriented. Don't paste their contents into demo-facing chat.

---

## Categories of planted behavior (principle + pointers)

This is a map, not an exhaustive list. Each service's own `CLAUDE.md` documents its specifics.

| Category | Lives in | Controlled by | Details |
|----------|----------|---------------|---------|
| Artificial AI latency (specialist bottleneck) | `support_service/` | `ASSISTANT_B_DELAY_SECONDS` env var | [support_service/CLAUDE.md](support_service/CLAUDE.md) |
| Rogue AI risk agent (declines ~90%+) | `support_service/`, `risk_assessment_service/` | scenario-service `risk-assessment/rogue-agent` | [support_service/CLAUDE.md](support_service/CLAUDE.md) |
| Injected payment failures (timeout / decline / stolen card) | `bill_pay/` | scenario-service `payment-scenarios` | [bill_pay/CLAUDE.md](bill_pay/CLAUDE.md) |
| DB connection-pool stress + LCP A/B slowness | `accounts_service/` | scenario-service `ab-testing` | [accounts_service/CLAUDE.md](accounts_service/CLAUDE.md), [docs/DATABASE_POOL_SCENARIO.md](docs/DATABASE_POOL_SCENARIO.md) |
| DB lock contention / slow queries | `transaction_service/` | request-triggered endpoints | [transaction_service/CLAUDE.md](transaction_service/CLAUDE.md) |
| Blocking request handling + HTTP error injection | shared `utils/process_headers.py` | `extra-transaction-time` / `error` request headers | see below |
| Frontend perf (LCP delay, blocking INP, broken toggle) | `frontend_service/` | backend-driven + keyword-triggered | [frontend_service/CLAUDE.md](frontend_service/CLAUDE.md) |
| Chaos experiments (pod-kill, CPU/mem stress) + db-360 load | `scenario_service/` control plane | scenario-service API + `flow-*.yml` | [scenario_service/CLAUDE.md](scenario_service/CLAUDE.md) |
| Tight resource limits (e.g. MSSQL memory, CPU-only limits) | `k8s/base/` | always-on | per-service CLAUDE.md |

### Shared behavior: `utils/process_headers.py`

Several FastAPI services (`accounts_service`, `auth_service`, `bill_pay`, `support_service`,
`transaction_service`) call `process_headers(...)` on inbound requests. It intentionally:

- performs a **blocking `time.sleep()`** for the number of seconds in the `extra-transaction-time`
  header (blocks the whole worker thread — this is deliberate, to create latency telemetry), and
- **raises an arbitrary HTTP error** when an `error` header with a 4xx/5xx status is present.

This is a demo hook. Leave it in place; don't make it async or remove the sleep.

**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Blocking delay*
  - *Present verbatim:* "Stop the request-preprocessing middleware from blocking the worker thread
    while handling inbound requests."
  - *Internal (do not surface):* `utils/process_headers.py` → `process_headers()` (~line 51) — delete
    the `if extra_transaction_time > 0: … time.sleep(extra_transaction_time)` block.
- *HTTP errors*
  - *Present verbatim:* "Stop the request preprocessor from short-circuiting valid requests with
    unexpected HTTP error responses."
  - *Internal (do not surface):* `utils/process_headers.py` → `process_headers()` (~lines 54–80) —
    remove the `if error_header:` block.

---

## Service index

Each service has its own `CLAUDE.md` with its specific demo behaviors and local-dev notes:

- [`accounts_service/`](accounts_service/CLAUDE.md) — accounts (FastAPI + PostgreSQL); LCP A/B + DB pool stress
- [`auth_service/`](auth_service/CLAUDE.md) — authentication (FastAPI)
- [`bill_pay/`](bill_pay/CLAUDE.md) — bill payments (FastAPI); payment failure scenarios
- [`frontend_service/`](frontend_service/CLAUDE.md) — React Router v7 SPA; browser RUM demo behaviors
- [`notifications_service/`](notifications_service/CLAUDE.md) — Kafka notifications; chaos target
- [`risk_assessment_service/`](risk_assessment_service/CLAUDE.md) — AI payment risk; rogue-agent path
- [`scenario_service/`](scenario_service/CLAUDE.md) — **the demo control plane** (injects everything)
- [`scheduler_service/`](scheduler_service/CLAUDE.md) — scheduled payments via Kafka; chaos target
- [`support_service/`](support_service/CLAUDE.md) — LangGraph multi-agent AI; specialist delay + rogue agent
- [`transaction_service/`](transaction_service/CLAUDE.md) — transactions (FastAPI + MSSQL); lock contention

Infra-only directories (`kafka_service/`, `otel_collector_kafka/`, `otel_collector_mssql/`) and the
`demo_flows/` load generators have no application source to "fix" and intentionally have no
`CLAUDE.md`.

---

## Using the New Relic MCP server

The New Relic MCP server is the **intended path** for diagnosis during demos. Prefer it over
guessing from source. Typical flow: find the entity, pull golden metrics / transactions / logs /
errors for the relevant window, correlate against a deployment or scenario change, then form a
hypothesis and **proactively propose a fix** (the intended finale). When the diagnosis maps to a
documented planted behavior, present that behavior's **pre-baked `Remediation`** (from the service
`CLAUDE.md`) **through plan mode** rather than re-deriving it or building a bespoke plan — see Prime
Directive point 3 for the exact EnterPlanMode → ExitPlanMode flow. Keep the narrative grounded in the
telemetry.

### ⏱️ Honor the user's time window — strictly

When the user specifies a time range ("last 3 hours", "since 9am", "yesterday", an explicit
window), that range is a **hard boundary for the entire investigation**. Every MCP tool call must
stay inside it. This is your responsibility, not the tools' — the New Relic tools faithfully honor
whatever bounds you pass, but several **default to their own lookback when you omit the window**
(e.g. `list_recent_issues` / `search_incident` → ~24h, `generate_alert_insights_report` → ~30 days,
the `analyze_*` tools → ~60 min after the start). Omitting the window is the main way you end up
looking beyond what the user asked.

Rules:

1. **Resolve the window once, up front.** Convert the user's phrase to explicit epoch bounds with
   `convert_time_period_to_epoch_ms`, then reuse those exact `start_time_ms` / `end_time_ms` on
   **every** call for the rest of the investigation.
2. **Always pass the window explicitly** — never rely on a tool's default lookback, even for a quick
   check. For tools that take `history_period_hours` / `history_period_minutes`, set them to match;
   for NRQL (`execute_nrql_query`, `natural_language_to_nrql_query`), pin `SINCE` **and** `UNTIL` to
   the same bounds rather than leaving an open-ended or wider `SINCE`.
3. **Never widen the window on your own.** If the requested range returns little or nothing, say so
   and ask before expanding — don't silently reach further back to "find something."
4. **Work within tool caps, don't exceed the ask.** Some tools warn against windows larger than
   1 day (e.g. `analyze_entity_logs`, `analyze_transactions`). If the user's window is larger, split
   into consecutive sub-queries **inside** their range and aggregate — never query beyond it.
5. If **no** window is given, pick a sensible default for the demo, **state the window you used**,
   and keep it consistent across calls so results are comparable.

---

## Development & deployment basics

- **Run from the repo root**, not from a service subdirectory:
  ```bash
  skaffold dev
  ```
- **Debug with `kubectl`** (faster than parsing skaffold output):
  ```bash
  kubectl get pods -n relibank
  kubectl logs -n relibank deployment/<service> --tail=50 -f
  ```
- **The scenario control plane UI** is at `http://localhost:8000/scenario-runner/home` — use it to
  toggle demo scenarios rather than editing code.
- **Formatting:** `ruff format` for Python.
- See [`README.md`](README.md) for the full architecture and [`docs/`](docs/) for scenario runbooks.

---

## When in doubt

1. Assume a surprising behavior is an **intentional demo feature** until proven otherwise — check
   the relevant service `CLAUDE.md`, `scenario_service/`, and `docs/`.
2. Diagnose through New Relic telemetry; keep the demo illusion intact.
3. Ask the user before changing anything that looks like planted demo behavior.

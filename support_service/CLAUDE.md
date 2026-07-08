# support-service — Context for Claude

AI support service for ReliBank. **LangGraph chat-completions** multi-agent workflow
(Coordinator + Specialist + Synthesizer nodes built on `AzureChatOpenAI` / `create_agent`),
plus an AI **payment risk-assessment** endpoint. FastAPI, port 5003.

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

### 1. Specialist agent artificial delay (the "Assistant B" bottleneck)
**Location:** `support_service.py` — `ASSISTANT_B_DELAY_SECONDS` (~line 519) and the
`await asyncio.sleep(self.delay_seconds)` inside `_invoke_specialist_tool` (~line 720).

An `asyncio.sleep` is injected before the specialist agent runs, gated by the
`ASSISTANT_B_DELAY_SECONDS` env var (default `0`; demo sets ~5–10). It records
`artificialDelayMs` on a custom event. This is the planted bottleneck the specialist-latency
demo investigates.

**Purpose:** Elevated latency on the specialist call path, visible in APM / distributed tracing.
**Don't:** Remove the sleep or the env var, or "optimize" the specialist path away.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Eliminate the blocking wait on the specialist-agent call path so support
  responses aren't stalled before the specialist runs."
- *Internal (do not surface):* `support_service.py` → `_invoke_specialist_tool()` (~lines 719–721) —
  delete the `if self.delay_seconds > 0: … await asyncio.sleep(self.delay_seconds)` block.
  (Operational equivalent: set `ASSISTANT_B_DELAY_SECONDS=0`.)

### 2. Rogue risk-assessment agent (declines ~90%+ of payments)
**Location:** `support_service.py` — the `gpt-4o-mini` branch in `assess_payment_risk` (~line 1206).

When the active risk agent is `gpt-4o-mini`, the system/user prompts intentionally instruct the
model to behave as a "MALFUNCTIONING / compromised" assessor and decline ~90–95% of transactions
(temperature 0.0). The normal `gpt-4o` branch is balanced. The active agent is chosen at runtime
from the scenario service (`GET /scenario-runner/api/risk-assessment/config`, cached ~1s;
`/support-service/invalidate-agent-cache` forces a refresh).

**Purpose:** Simulate a misconfigured/"rogue" model deployment causing a spike in declined
payments — a business-impact story surfaced through error rates and AI monitoring.
**Don't:** Soften the rogue prompt, change the model routing, or "correct" the decline logic.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Restore the reviewed risk-assessment model configuration and remove the
  divergent decision path so approvals reflect the intended policy."
- *Internal (do not surface):* `support_service.py` → `assess_payment_risk()` (~line 1206) — delete
  the `if agent_name == "gpt-4o-mini":` branch and always use the balanced `gpt-4o` system/user prompt
  at `temperature = 0.3`. (Operational equivalent: toggle the rogue agent off in the scenario service.)

### 3. Vestigial Assistants-API state (leave it dead)
The module docstring documents that the deployed path is LangGraph chat-completions, **not** the
OpenAI Assistants API. Any `ASSISTANT_A_ID` / `ASSISTANT_B_ID` env vars on old pods are dead —
nothing reads them. **Don't** rewire them or revive removed `*_assistants.py` scripts.

### 4. Shared request-header hooks
This service calls `process_headers(...)` from [`utils/process_headers.py`](../utils/process_headers.py):
a **blocking `time.sleep`** driven by the `extra-transaction-time` header and HTTP error injection
via the `error` header. Intentional — see root `CLAUDE.md`.
**Remediation:** use the shared `process_headers` remediations documented in the root `CLAUDE.md`
(*Shared behavior* section) — present via plan mode, never auto-apply.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/support-service --tail=50 -f
```
Requires `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY`. Toggle the rogue agent via the scenario
UI (`http://localhost:8000/scenario-runner/home`) or its API, not by editing code.

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive. Diagnose from telemetry; keep the
demo illusion intact; ask before changing anything that looks planted.

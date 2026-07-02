# bill-pay-service — Context for Claude

Handles bill payments (bank + card via Stripe test tokens) and routes payments through
AI risk assessment. FastAPI, port 5000.

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

All three payment-failure scenarios live in `bill_pay_service.py`, are **probability-gated**
(`random.random() * 100 <= probability`), and are configured at runtime from the scenario service
(`payment-scenarios` config). Config fields are declared around lines 104–110; the checks fire in
the card-payment path around lines 641–719.

### 1. Gateway timeout (~line 696)
When enabled, `await asyncio.sleep(gateway_timeout_delay)` then raises **HTTP 504**. Records
`PAYMENT_GATEWAY_DELAY` / `PAYMENT_GATEWAY_TIMEOUT` events.
**Purpose:** Latency + timeout errors on the payment path.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Stop the card-payment path from stalling and timing out against the payment
  gateway."
- *Internal (do not surface):* `bill_pay_service.py`, card-payment path (~line 696) — delete the
  `gateway_timeout_enabled` block (the `await asyncio.sleep(delay)` + `raise HTTPException(504)`).
  (Operational equivalent: disable the `payment-scenarios` in the scenario service.)

### 2. Card decline (~line 647)
When enabled, returns a `card_declined` result and raises **HTTP 402**. Records `PAYMENT_DECLINED`.
**Purpose:** Elevated decline/error rate story.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Stop the card-payment path from declining otherwise-valid payments."
- *Internal (do not surface):* `bill_pay_service.py`, card-payment path (~line 647) — delete the
  `card_decline_enabled` block (the `raise HTTPException(402)`). (Operational equivalent: disable the
  `payment-scenarios` in the scenario service.)

### 3. Stolen card (~line 641)
When enabled, forces the Stripe test method `pm_card_visa_chargeDeclinedStolenCard` so the charge
is declined as fraud.
**Purpose:** Fraud-signature failures in payment telemetry.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "Stop the card-payment path from substituting the customer's selected payment
  method."
- *Internal (do not surface):* `bill_pay_service.py`, card-payment path (~line 641) — delete the
  `stolen_card_enabled` block so `payment_method_to_use = resolved_payment_method` always.
  (Operational equivalent: disable the `payment-scenarios` in the scenario service.)

> Note: a genuine Stripe decline elsewhere in the file (`status_code=402` around line 1018) is
> normal error handling, not a planted scenario.

### 4. Shared request-header hooks
Calls `process_headers(...)` from [`utils/process_headers.py`](../utils/process_headers.py):
blocking `time.sleep` (`extra-transaction-time` header) and HTTP error injection (`error` header).
Intentional — see root `CLAUDE.md`.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/bill-pay-service --tail=50 -f
```
Toggle scenarios via the scenario UI/API (`http://localhost:8000/scenario-runner/home`), not by
editing code. `bill-pay-service` is also a chaos-experiment target (pod-kill, memory stress).

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

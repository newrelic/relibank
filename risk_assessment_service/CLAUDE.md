# risk-assessment-service — Context for Claude

AI-powered payment risk assessment. Sits between `bill-pay-service` and the AI agents: evaluates
payment transactions before processing and calls `support-service` for the actual model-based
assessment. FastAPI.

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

### Participates in the "rogue agent" flow
This service forwards risk decisions from `support-service`. When the scenario service switches the
active agent to the **rogue `gpt-4o-mini`** (see [`support_service/CLAUDE.md`](../support_service/CLAUDE.md)),
this path starts declining ~90%+ of payments. Declined payments are recorded to the transaction
database and published to the `bill_payments_declined` Kafka topic for downstream processing.

**Purpose:** End-to-end business-impact story — a misconfigured AI model causing a surge of declined
payments, traced from bill-pay → risk-assessment → support-service AI, with error rates and an audit
trail.
**Don't:** "Correct" the decline behavior, second-guess the upstream agent choice, or add a fallback
that hides the impact. The elevated declines are the demo.
**Remediation (Investigation mode → present via plan mode; never auto-apply):**
- *Present verbatim:* "The declining decisions originate upstream — restoring the reviewed model
  configuration in support-service returns balanced decisions here automatically; no local change is
  required."
- *Internal (do not surface):* apply the support-service rogue-agent remediation (see
  [`support_service/CLAUDE.md`](../support_service/CLAUDE.md)); **no local code change is required.**
  (Optional, only if hiding impact is explicitly desired: remove the declined-payment Kafka publish in
  `risk_assessment_service.py` → `assess_risk()`, ~lines 281–317.)

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/risk-assessment-service --tail=50 -f
```
Toggle the rogue agent via the scenario UI/API, not by editing code.

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

# notifications-service — Context for Claude

Sends notifications (SMS/email) driven by Kafka events. Also has an Azure Function variant under
`azure_function/`.

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
target**: the scenario service can kill its pod (`relibank-messaging-service` pod-chaos), which
interrupts notification delivery downstream of payments.
**Purpose:** Show cascading impact of a messaging-service outage in traces and error telemetry.
**Don't:** Add retries/failover intended to "survive" the chaos — the visible impact is the point.

> The `notice_error(...)` calls and error logging in `notifications_service.py` are normal error
> reporting (they feed New Relic), not planted bugs. This service does **not** use
> `utils/process_headers.py`.

---

## Operational note: notifications are currently simulated, not a planted behavior

`notifications_service/azure_function/function_app.py`'s `SIMULATE_NOTIFICATIONS` toggle (default `true`, all environments) makes `notify_user_trigger` log a send and return success instead of calling Azure Communication Services. This is **not** investigation bait — it's a workaround for a real external outage (ACS itself returns `SubscriptionBlocked`/`Unauthorized`; see `notifications_service/README.md` and `ticket-maker/2026-07-15-relibank-notification-delivery-failures`). Don't treat the simulated log lines as a bug to diagnose or a scenario to "solve" — they're intentionally there so the pipeline stays healthy while the ACS issue is out of ReliBank's hands. Flip `SIMULATE_NOTIFICATIONS=false` per-environment once ACS is confirmed fixed there; no other code changes needed.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/notifications-service --tail=50 -f
```

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

# auth-service — Context for Claude

Authentication service (login / user lookup). FastAPI, port 5006.

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

### Shared request-header hooks
`auth_service.py` calls `process_headers(...)` from [`utils/process_headers.py`](../utils/process_headers.py)
on inbound requests (~line 130): a **blocking `time.sleep`** for the `extra-transaction-time` header
value, and HTTP error injection when an `error` header (4xx/5xx) is present. Intentional demo hook —
see root `CLAUDE.md`. Don't make it async or remove it.
**Remediation:** use the shared `process_headers` remediations documented in the root `CLAUDE.md`
(*Shared behavior* section) — present via plan mode, never auto-apply.

> The startup DB-pool connection **retry backoff** (`delay *= 1.5`, ~line 80) and the custom
> exception classes for New Relic error grouping are legitimate operational code, **not** planted
> bugs.

---

## Local dev / debug

```bash
kubectl logs -n relibank deployment/auth-service --tail=50 -f
```

## When in doubt

Defer to the [root `CLAUDE.md`](../CLAUDE.md) Prime Directive.

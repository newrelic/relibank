# Contributing to ReliBank

ReliBank is maintained by the demo-engineering team as a New Relic sales-demo application. If
you're a sales engineer running a live demo, you don't need this file — see the root
[`CLAUDE.md`](CLAUDE.md) instead. This file is for the ~6-person team building and maintaining
the app itself ("Builder mode" — see [`CLAUDE.md`](CLAUDE.md#-modes--read-this-first-it-decides-how-the-prime-directive-applies)
and the `/build-mode` skill).

## Dev loop

Run everything from the repo root:

```bash
skaffold dev
```

Use `kubectl` for faster iteration than parsing Skaffold's own output:

```bash
kubectl get pods -n relibank
kubectl logs -n relibank deployment/<service> --tail=50 -f
```

The scenario control plane UI (`http://localhost:8000/scenario-runner/home`) toggles demo
behaviors at runtime — prefer it over editing code when you just need a scenario on/off.

## Adding or changing a planted demo behavior

Follow [`docs/SCENARIO_AUTHORING.md`](docs/SCENARIO_AUTHORING.md) — it covers the
config → endpoints → consumer → docs → optional workflow pattern used across
`scenario_service/` and the services it drives. The `scenario-author` subagent can drive that
flow end-to-end if you're working with Claude Code.

When you add or change a planted behavior, update the relevant service's `CLAUDE.md` (and, for
cross-cutting changes, the root `CLAUDE.md`) so Investigation-mode sessions stay accurate.

## Testing

See [`tests/README.md`](tests/README.md) for the end-to-end test suite (setup, running, and
what's covered) and [catapult-service's testing-runbook.md](https://github.com/newrelic/catapult-service/blob/main/relibank_deployer/docs/testing-runbook.md) for
deployer-specific validation.

## Formatting

Python: `ruff format` before committing.

## Deployer changes

The multi-env blue/green deployer and its Terraform no longer live in this repo — they moved to
`catapult-service` (`relibank_deployer/`). If your change touches the deployer itself, read
[catapult-service's deployer_primer.md](https://github.com/newrelic/catapult-service/blob/main/relibank_deployer/docs/deployer_primer.md)
first (the *why*) and [runbook.md](https://github.com/newrelic/catapult-service/blob/main/relibank_deployer/docs/runbook.md)
(the *how*).

If your change touches deployer-*consumed* code that stays here instead — `tests/`
(particularly `tests/workflow_validation/validate_nr_workflow.py`, which catapult-service's
`Deploy ReliBank NR` workflow checks out and runs directly) or the Python/frontend test suites —
make sure it stays compatible with catapult-service's native `post-deployment-tests` /
`post-deployment-frontend-tests` jobs, since those are what actually exercise this code now.

## PR norms

Keep planted-behavior changes deliberate, not incidental — call out in the PR description if a
change alters what a live demo shows. Small, scoped PRs per service are preferred over
sprawling cross-service changes.

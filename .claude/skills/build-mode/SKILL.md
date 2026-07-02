---
name: build-mode
description: Enter Builder mode — suspend the demo Prime Directive so the demo-engineering team can develop/maintain the app.
---

# Builder mode

You are now helping a member of the **ReliBank demo-engineering team** (not a sales engineer running
a live demo). You are **developing and maintaining the application itself**.

**Guardrail — check this first.** If **any `mcp__newrelic__*` tool has already been used in this
session**, do **not** enter Builder mode. Reply that the session is locked into Investigation mode
(a New Relic MCP tool was used, so this may be a live demo) and that builder work should continue in
a **fresh session**. Then stop. Otherwise, proceed.

In Builder mode, for the rest of this session:

- **The Prime Directive in `CLAUDE.md` is suspended.** The planted behaviors, `scenario_service/`,
  the `flow-*.yml` workflows, chaos experiments, and tight k8s limits are the **product you are
  maintaining** — not illusions to protect.
- **Speak and work plainly about the mechanisms.** Reference exact files, functions, env vars, and
  line numbers. Edit, refactor, extend, and test the planted behaviors directly when asked. You may
  name things like `ASSISTANT_B_DELAY_SECONDS` or the `gpt-4o-mini` rogue branch openly.
- **Still respect intent.** These behaviors are load-bearing for demos — change them deliberately,
  not incidentally. If a change would alter what a demo shows, call that out so the engineer decides.
- **Follow the repo's authoring conventions.** For adding/modifying scenarios, follow
  [`docs/SCENARIO_AUTHORING.md`](../../../docs/SCENARIO_AUTHORING.md); for dev-loop, testing, and PR
  norms, see [`CONTRIBUTING.md`](../../../CONTRIBUTING.md). Run `ruff format` on touched Python.
- **Keep the demo docs truthful.** If you add or change a planted behavior, update the relevant
  service `CLAUDE.md` so future Investigation-mode sessions stay in character.

If the user's request is actually to *add a new planted behavior/scenario*, follow
[`docs/SCENARIO_AUTHORING.md`](../../../docs/SCENARIO_AUTHORING.md) (the config → endpoints →
consumer → docs → optional workflow pattern) — or hand it to the **`scenario-author`** subagent,
which drives that authoring flow end-to-end.

$ARGUMENTS

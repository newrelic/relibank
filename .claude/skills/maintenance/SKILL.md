---
name: maintenance
description: Run the ReliBank upgrade maintenance end to end — New Relic agents (the Python APM agent in the exact-pinned services, the Browser agent loader in the frontend) and package/library updates (every Python service's requirements.txt and the frontend's npm packages) — as separate commits on one new local branch, then validate the result by deploying it to the local docker-desktop cluster and comparing the data in New Relic with a production baseline taken before any change. It resolves problems itself (fallback releases, whole-family updates, a small documented code adaptation) and stops only when something is definitely broken and cannot be resolved. The only thing it ever asks the person for is connecting the New Relic MCP. It never pushes: the final report prints the push command, so the manual steps left are reviewing the branch, pushing it and opening the PR. Use when the user asks to upgrade New Relic agents, bump NR versions, update dependencies or packages, validate a maintenance branch, or run the maintenance runbook. An argument of agents or packages runs only that phase; baseline captures only the production baseline and changes nothing. nri-bundle, nr-ebpf-agent, the NRDOT collector and the Dockerfile-pinned collectors are checked and reported, never edited.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Glob
  - Grep
  - ToolSearch
  - mcp__newrelic__list_available_new_relic_accounts
  - mcp__newrelic__execute_nrql_query
  - mcp__newrelic__get_entity
---

# Maintenance Skill (agents + packages)

Upgrade the New Relic agents **and** update the packages across ReliBank **autonomously**: pick the versions, make the changes, verify them, fix what breaks, and commit to a new local branch. Nothing leaves the machine: the user reviews the branch, pushes it with the command the final report prints, and opens the PR.

This skill replaces `nr-upgrade` and `pkg-update` (and the generic `nr-agent-upgrade` / `package-update`). It has no confirmation prompts and no "review before commit" pauses.

The work is two phases, each its own commit(s), so the small high-risk agent change stays reviewable, revertable and deployable on its own:

| Phase | Commit(s) | Content |
|---|---|---|
| A — Agents | `chore: new relic python agent upgrade YYYY-MM-DD` and `chore: new relic browser agent upgrade YYYY-MM-DD` | `newrelic==` in six services; the Browser agent loader `frontend_service/app/nr.js` |
| B — Packages | `chore: package and library updates YYYY-MM-DD` | Python `requirements.txt` floors, frontend npm packages — **never** touching an agent version |

Scope comes from the invocation text: `agents` → Phase A only, `packages` → Phase B only, `baseline` → Step 0 only (capture the production baseline and stop), anything else → both phases. Never ask which. Every scope that changes code ends with Steps 8 and 8b.

**How this repo differs from a lockfile repo (verified 2026-11-08).** Python manifests are floors (`fastapi>=0.141.1`) with no lock file, and the Dockerfiles run `pip install -r`, so **every image build already installs the newest release of everything**: a dry-run resolve of the untouched `main` gives `support_service` `openai 3.46.0`, `langgraph 1.2.20` and `fastapi 0.162.2`. Raising a floor therefore changes the manifest, not what runs. The proof that matters is that *today's fresh resolve still installs and starts*, and the report compares the **resolved set before and after**, not just the manifest diff. Only exact pins (`newrelic==`, `httpx==0.27.0`) change what runs. The frontend does have a lock file (`package-lock.json`), so npm updates are real changes.

## Operating Mode

- **Never ask the user anything and never wait for approval — with one exception: Step 0.** The New Relic MCP is a prerequisite the skill cannot satisfy itself; if it is not connected, ask the person to connect it (once, before anything is created) and stop. Every other choice is made by the rules below; record each decision for the final report.
- **Resolve, don't skip.** When a unit is blocked, work down this ladder and take the first rung that passes every check, then say which rung you took: (1) the newest release; (2) the newest compatible release, or a whole family updated together; (3) adapt — either a small documented code change in the failing service (see "Code adaptation") or raise a base image (`python:3.12`, `node:24-alpine`) by **one minor/LTS step**, only when a needed package requires it and only to a stable tag that exists, as its own commit flagged `BREAKING RISK`; (4) hold it with a stated reason — majors beyond policy, pre-releases, caps, and anything that needs a design decision stay here. At most 3 candidates and one code adaptation per unit. A skipped unit with no reason is a bug.
- **Target = the newest stable release that passes the rules.** Pre-releases are never chosen. Python agent majors are allowed (call them out); npm packages stay within minor/patch (newer majors are listed as `HELD`); Python floors take the newest stable.
- **Units of upgrade.** Phase A: the Python agent across all six services (together or none), the Browser loader. Phase B: one Python service, or the frontend. If a unit cannot be upgraded safely after the fallbacks, revert exactly that unit's files, record why, and continue. Never leave a unit half-edited.
- **Baseline rule for checks.** Run every check once **before any change** (Step 2). After the change a check must be no worse: something that passed must still pass; a check that already failed on baseline only has to not get worse. Record "not runnable here" in the report instead of treating it as a failure.
- **Highlight breaking changes.** Anything rejected or restored because it failed to install, build, test or start is `BREAKING — blocked`; passing agent/package majors and `0.x` bumps are `BREAKING RISK — included`; caps, pins and resolution conflicts are `HELD`. The report and the PR body open with these.
- **Verify the application, not just the packages.** Step 8 compares the whole application with the baselines recorded in Step 2. A regression restores the affected unit and is reported as `BREAKING — blocked`.
- **Validate the telemetry, not just the build.** Step 0 records a production baseline in New Relic before any change; Step 8b deploys the finished branch to the local docker-desktop cluster, drives the repo's own test suite as traffic, and compares APM, golden signals, logs, traces, errors, agent versions and saturation with that baseline. A parity failure is `NEEDS REVIEW`; a service that stops reporting is `BREAKING — blocked`.
- **Independent.** This skill depends on no other skill, memory or earlier run — only on the New Relic MCP for Steps 0 and 8b. Its baselines, scripts and rules are all in this file.
- Stop early only when nothing changed (no branch is kept), or when the application gate still fails after restoring the regressed units (the branch is kept locally, marked NOT READY, and no push command is printed). Say so in the report.

**HARD RULES:**
- Work only in a git worktree on a **new** branch `chore/maintenance-YYYYMMDD` created from `origin/main`. Never commit to `main` or any existing branch. The user's checkout (it may hold uncommitted work) is never touched.
- **Never push**: no `git push` of any kind. Remote access is read-only (`git fetch`, `git ls-remote`, `gh pr list` / `gh pr view`, `gh api` GETs). **Never** create the PR (`gh pr create`) or dispatch/trigger any workflow or deployment to any environment.
- **`docker-desktop` is the only cluster this skill may read or write, and it has full control of it** (granted by the user, 2026-11-08). `kubectl`, `skaffold`, `helm` and `docker` may touch only that cluster, through a throwaway kubeconfig that contains that one context (built in Step 8b) and is exported as `KUBECONFIG` for every command. This machine's kubeconfig also holds production clusters: never switch contexts, never pass `--context`, `--kube-context` or `--kubeconfig`, never read `~/.kube/config`, and re-check before each cluster command that `kubectl config get-contexts -o name` prints only `docker-desktop`. Any other cluster, in any form, is off limits for reading as well as writing. **An old deployment found on `docker-desktop` is taken down and replaced, without asking** (Step 8b "Take down an old deployment"). Only `docker-desktop` namespaces `relibank`, `chaos-mesh` and `newrelic` and the helm releases inside them are in scope; `default`, `kube-*` and anything else are never touched. If the one-context kubeconfig cannot be built, or its server is not `127.0.0.1`, skip Step 8b and say so.
- **New Relic access is read-only** (NRQL and entity reads). Never create or change anything in New Relic. Test data goes only to the Local account; if `skaffold.env` points at any other account, skip Step 8b. Never print, log or commit a license key, API key, `skaffold.env` or the generated `k8s/base/infrastructure/newrelic/nrdot-mssql.env`.
- Stage only the files this skill is expected to change (per-commit allow-lists below). Never `git add -A` / `git add .`.
- Phase B must never change an agent version (`newrelic==`, the `nr-loader-spa-*` loader, `@newrelic/browser-agent`).
- **Planted demo behavior is off limits.** ReliBank ships deliberate problems (see the root `CLAUDE.md`). Maintenance never edits what implements them: `utils/process_headers.py`, `scenario_service/` (except its `requirements.txt`), `.github/workflows/flow-*.yml`, `scenario_service/chaos_mesh/`, the resource limits in `k8s/base/`, and anything a service `CLAUDE.md` documents as a planted behavior. If an upgrade breaks one of them, hold that unit (rung 4) and report it in production terms (e.g. "payment failure rate stopped reproducing after the `<package>` bump"), never by describing the mechanism.
- **Mode.** This is Builder-mode work: start it in a fresh session. Using the New Relic MCP trips this repo's Investigation-mode hook (`.claude/settings.json`); that is expected and compatible with this skill, which only reads telemetry, never edits planted behavior, and reports in production terms.

## Escalation Contacts

| Notify / Escalate | Contact |
|---|---|
| Gabe Alabastro (@galabastro), Jared Goddard (@jgoddard), Shakthi Manjunathan (@smanju) | #tech-marketing-internal |

---

## Service Map

All services are at the repo root (`$WT` below is the worktree):

| Service | Agent (Phase A) | Packages (Phase B) |
|---|---|---|
| `accounts_service`, `auth_service`, `bill_pay`, `notifications_service`, `scheduler_service`, `transaction_service` | Python APM: `requirements.txt` `newrelic==` (exact, all six equal) | `requirements.txt` floors |
| `support_service` | `newrelic>=13.6.1` is a **floor with a documented reason** (needs the LangChain/LangGraph instrumentation; "confirmed working live in sandbox"). **Never edited**; the version that actually runs is recorded in Step 8b | `requirements.txt`; the AI family (`openai`, `langgraph`, `langchain`, `langchain-core`, `langchain-openai`) moves together or not at all |
| `risk_assessment_service` | none (covered by nr-ebpf-agent) | `requirements.txt` |
| `scenario_service` | none | `requirements.txt` (exact pin `httpx==0.27.0` is tried like any package) |
| `frontend_service` | Browser agent loader `app/nr.js` (+ the `@newrelic/browser-agent` declaration in `package.json`, which no app code imports) | `package.json`, `package-lock.json` |
| `notifications_service/azure_function` | none | `requirements.txt` has no version specifiers: nothing to edit |
| `tests/` | none | **skip** — test-only dependencies, not a service |

**Checked and reported, never edited** (Step 3 prints current vs newest):
- `nri-bundle` / `nr-ebpf-agent`: `terraform/aks/newrelic/nr_infra_agent.tf` has `version = "^8.0.0"`, a caret range that already floats to every 8.x on each apply (latest on 2026-11-08: `8.0.40`). Only a new **major** needs a deliberate change plus the `ReliBank NR` workflow. (The old `nr-upgrade` skill said the resource has no `version` line; that is outdated.)
- The NRDOT collector (`otel_collector_mssql/Dockerfile` downloads the latest release at build) floats on its own.
- Dockerfile-pinned collectors in `otel_collector_kafka/Dockerfile`: `OTEL_VERSION` (0.145.0) and `JMX_SCRAPER_JAR_VERSION` (1.52.0), and the base images (`python:3.12`, `node:24-alpine`, `bitnamilegacy/kafka:3.5`, `postgres:15`, `mssql/server:2022-latest`).

---

## Pins and Invariants — enforce silently, never skip

### Python
- `newrelic` is Phase A's. Phase B passes `--skip newrelic` everywhere.
- Caps are decisions: `gunicorn>=23.0.0,<24` (support, scenario) stays; `pur` keeps caps. Never remove or widen one; list the newer release as `HELD`.
- Exact pins other than the agent (`httpx==0.27.0`, added with the scenario page, no recorded reason) are tried: kept only if the resolve, install, import and local deploy all pass; otherwise restored and listed `HELD` with the failing line.
- `pydantic>=2.12.0a1` (support) is a pre-release floor; it becomes the newest stable.
- Run installs on the Dockerfile's Python (3.12). A release whose `Requires-Python` excludes 3.12 fails the resolve and falls back.

### Frontend (npm)
- `npm-check-updates --target minor`: majors are never applied and are listed `HELD` with their version (on 2026-11-08: `react-router` 8, `@mui/*` 9, `vite` 8, `vitest` 5, `typescript` 7, `jest-dom` 7).
- `@newrelic/browser-agent` is rejected from the bulk update (Phase A owns it). When the lock is regenerated its entry may move inside its own `^` range; that is not an agent change (nothing imports the package; the loader in `nr.js` is the runtime agent), which is why Step 7 does not look in the lock for it.
- The router family (`react-router`, `react-router-dom`, `@react-router/*`) moves together. Verified 2026-11-08: bumping it against the existing lock fails with `ERESOLVE` on npm 10 **and** npm 11; regenerating the lock resolves it (see 6b).
- **Run every npm command inside `node:24-alpine`** (the Dockerfile's image). The host's Node 20.8 / npm 10.1 crashes on installs (`Cannot read properties of null (reading 'edgesOut')`).
- `npm run build:mfe:*` rewrites the **committed** bundles under `frontend_service/public/microfrontends/` and adds `.js.map` files. Restore them after every build (`git checkout -- frontend_service/public && git clean -fdq frontend_service/public`); never commit them. The gate script below does this.
- `@testing-library/jest-dom` is an exact pin (`6.9.1`, set by the previous manual maintenance, reason not recorded): tried like any package, kept only if the gate passes.

### Browser agent loader (`frontend_service/app/nr.js`)
`nr.js` = a prefix (`NREUM.init`, `loader_config`, `info`, carrying the four `__ACCOUNT_ID__` / `__TRUST_KEY__` / `__APPLICATION_ID__` / `__LICENSE_KEY__` placeholders that `generate_nrjs_file.sh` substitutes at image build — never put real values in the file) + the published `https://js-agent.newrelic.com/nr-loader-spa-<version>.min.js` + one local edit (`feature_flags:[]` → `feature_flags:["register"]`). Verified 2026-11-08: `1.312.1` is reproduced byte for byte that way. The script in 4b refuses to touch a file it cannot reproduce, so a hand edit is never silently dropped.

---

## Workflow

Shell state does not persist between tool calls: print `REPO`, `BRANCH`, `WT`, `B`, `NR` in Step 1, remember them, and set them again (or use literal paths) at the start of every later command. Run the scripts below with `bash`. Allow long timeouts (up to 10 minutes) for installs and gates; run `skaffold run` with `run_in_background`.

### Step 0: Preflight and production baseline (before anything is created)

Runs first for every scope. `NR=$(mktemp -d)` holds everything this step records; remember the path.

**0a. Connect check — the only question this skill ever asks.** Load the tools with `ToolSearch` (`select:mcp__newrelic__list_available_new_relic_accounts,mcp__newrelic__execute_nrql_query,mcp__newrelic__get_entity`). If they do not load, stop before creating anything and tell the person: *"The New Relic MCP isn't connected. Run `/mcp`, pick `newrelic`, authenticate, then run `/maintenance` again. Reply `continue without baseline` to run anyway; the report will say NO BASELINE and Step 8b will skip the comparison."* Only that reply lets the run continue.

**0b. Accounts.** `list_available_new_relic_accounts`, then match by name: `Demogorgon Prod` (the baseline; the repo's docs record id 4120837) and `Demogorgon Local` (where Step 8b sends data; 4182956). Match on the **name**; if the id differs from the documented one, say so in the report and carry on. A name that is missing marks that part NOT AVAILABLE. Never guess an id.

**0c. Production baseline** (read-only, account `Demogorgon Prod`, `SINCE 1 hour ago`; golden signals and error classes again for `24 hours ago`). That account also holds the Demogorgon and ReliFarm apps: always filter by name.
1. Find the production app names: `SELECT uniques(appName, 50) FROM Transaction WHERE appName LIKE 'ReliBank (Prod) - %' SINCE 1 day ago`. Expect seven: `Accounts Service`, `Auth Service`, `Bill Pay Service`, `Event Scheduler Service`, `Notifications Service`, `Support Service`, `Transaction Service` after the `ReliBank (Prod) - ` prefix. Call the list `$APPS`; the suffix is the key used to match local names later. None found → NO BASELINE (do not ask), continue.
2. Run the table. Both deploy colors report under the same app names, so facet by app only.

| # | Signal | NRQL (or tool) |
|---|---|---|
| 1 | APM golden signals | `SELECT count(*) AS requests, percentage(count(*), WHERE error IS true) AS errorRate, average(duration) AS avgSec, percentile(duration, 95) AS p95, apdex(duration, t: 0.5) AS apdex, rate(count(*), 1 minute) AS rpm FROM Transaction WHERE appName IN ($APPS) FACET appName, transactionType` |
| 2 | APM metrics | `SELECT count(apm.service.transaction.duration) AS samples, average(apm.service.transaction.duration) AS avgSec FROM Metric WHERE appName IN ($APPS) FACET appName` — APM metric queries need an explicit `appName IN (...)`; wildcards fail with "No application was matched" |
| 3 | **Agent versions** | Not in any event. `SELECT latest(entity.guid) FROM Span WHERE entity.name IN ($APPS) FACET entity.name`, then `get_entity` per guid and read the tag `agentVersion` (it can lag or blend the two deploy colors: informational) |
| 4 | Logs and log-to-trace linking | `SELECT count(*) AS logs, filter(count(*), WHERE trace.id IS NOT NULL) AS withTraceId FROM Log WHERE entity.name IN ($APPS) FACET entity.name` |
| 5 | Traces and depth | `SELECT uniqueCount(trace.id) AS traces, count(*) AS spans FROM Span WHERE entity.name IN ($APPS) FACET entity.name`; depth: `FROM (SELECT uniqueCount(entity.name) AS services FROM Span WHERE entity.name IN ($APPS) FACET trace.id LIMIT MAX) SELECT count(*) AS traces, average(services), max(services), percentage(count(*), WHERE services >= 2), percentage(count(*), WHERE services >= 3)` — the subquery must not carry its own `SINCE` (syntax error); append `SINCE 1 hour ago` after the outer `SELECT`, or leave it off |
| 6 | Error classes | `SELECT count(*) FROM TransactionError WHERE appName IN ($APPS) FACET appName, error.class, error.message LIMIT 25` (24 h) |
| 7 | Datastores | `SELECT count(*) FROM Span WHERE entity.name IN ($APPS) AND (category = 'datastore' OR db.system IS NOT NULL) FACET entity.name, db.system` |
| 8 | Saturation and pods | `SELECT uniqueCount(podName) AS pods, max(restartCount) AS maxRestarts, average(memoryWorkingSetBytes)/1048576 AS avgMemMB, max(memoryWorkingSetBytes)/1048576 AS maxMemMB, max(timestamp) AS last FROM K8sContainerSample WHERE namespaceName LIKE 'relibank-%' FACET clusterName, deploymentName`. If a deployment appears under two cluster names, keep the row with the newer `last` |
| 9 | Browser | `SELECT count(*) FROM PageView, BrowserInteraction, JavaScriptError, AjaxRequest WHERE appName = 'ReliBank (Prod) - Customer Portal' FACET eventType()` and `SELECT uniques(agentVersion) FROM PageView WHERE appName = 'ReliBank (Prod) - Customer Portal'` |
| 10 | Alerts | `SELECT filter(uniqueCount(issueId), WHERE event = 'activate') AS opened, filter(uniqueCount(issueId), WHERE event = 'close') AS closed FROM NrAiIssue FACET priority` (24 h). Do not use `list_recent_issues`: it can overflow the tool's token limit on this account |
| 11 | Integrations present | `SELECT count(*) FROM PostgresqlDatabaseSample` and `SELECT count(*) FROM Metric WHERE metricName LIKE 'sqlserver.%' OR metricName LIKE 'kafka.%'` |

**0d. Record it.** Write `$NR/baseline-prod.md` (one table per row above) and keep the numbers in your notes; the final report quotes them. Also write down what is *normal*, so nobody blames the upgrade: production carries scheduled load and fault injection from the `flow-*.yml` workflows, so its error rate and latency are higher than a quiet local stack. Step 8b therefore compares **one-sidedly** (local must not be worse than prod), and only prod's error classes count as "known".

With scope `baseline`, print the tables and stop.

### Step 1: Isolated branch

```bash
REPO=$(git rev-parse --show-toplevel); cd "$REPO"
git fetch origin main
DATE=$(date +%Y%m%d); BRANCH=chore/maintenance-$DATE; n=2
while git show-ref --verify --quiet "refs/heads/$BRANCH" || git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; do BRANCH=chore/maintenance-$DATE-$n; n=$((n+1)); done
WT=$(mktemp -d)/relibank; B=$(dirname "$WT")
git worktree add -b "$BRANCH" "$WT" origin/main
echo "REPO=$REPO BRANCH=$BRANCH WT=$WT B=$B NR=$NR"
```

Collision check (informational — never blocks): open PRs already touching these files will conflict with this branch. List any hits in the report (a previous maintenance PR, `chore/maintenence-20261009`, was still open on 2026-11-08).
```bash
gh pr list --state open --limit 100 --json number,title,headRefName,files --jq '.[] | select(any(.files[]?; .path | test("(^|/)requirements\\.txt$|frontend_service/(package(-lock)?\\.json|app/nr\\.js)$"))) | "#\(.number) \(.headRefName) | \(.title)"'
```

### Step 2: Baselines (before any change)

Write the two gate scripts once, then run them on the untouched tree. Both write comparable *tokens* (`<service> INSTALL=OK`, …); a regression later is a token that was present on baseline and is missing now.

```bash
cat > "$B/smoke.sh" <<'EOF'
#!/bin/bash
# usage: smoke.sh <tree> <label> [service ...]
# Mimics the Dockerfiles for each Python service: fresh Python 3.12 venv, pip install -r requirements.txt, pip check, import the app module.
# Prints one line per service and writes the comparable tokens to $(dirname <tree>)/tokens-py-<label>.txt
T=$1; L=$2; shift 2; O=$(dirname "$T"); TK=$O/tokens-py-$L.txt; : > "$TK"; PY=$(command -v python3.12 || command -v python3)
for entry in accounts_service:accounts_service auth_service:auth_service bill_pay:bill_pay_service notifications_service:notifications_service risk_assessment_service:risk_assessment_service scenario_service:scenario_service scheduler_service:scheduler_service support_service:support_service transaction_service:transaction_service; do
  svc=${entry%%:*}; mod=${entry##*:}
  [ $# -gt 0 ] && ! printf '%s\n' "$@" | grep -qx "$svc" && continue
  cd "$T/$svc" || continue; V=$O/sv-$svc/bin; $PY -m venv "$O/sv-$svc" >/dev/null 2>&1; note=""
  if "$V/pip" install -q -r requirements.txt >"$O/pip-$L-$svc.log" 2>&1; then
    echo "$svc INSTALL=OK" >> "$TK"; "$V/pip" freeze > "$O/freeze-$L-$svc.txt"
    if "$V/pip" check >"$O/check-$L-$svc.log" 2>&1; then echo "$svc PIPCHECK=clean" >> "$TK"; else note="$note pip check: $(head -1 "$O/check-$L-$svc.log" | cut -c1-90);"; fi
    if PYTHONPATH="$T" "$V/python" -c "import $mod" >"$O/imp-$L-$svc.log" 2>&1; then echo "$svc IMPORT=OK" >> "$TK"
    elif grep -q libodbc "$O/imp-$L-$svc.log" && PYTHONPATH="$T" "$V/python" -c "import sys,types; sys.modules['pyodbc']=types.ModuleType('pyodbc'); import $mod" >/dev/null 2>&1; then echo "$svc IMPORT=OK" >> "$TK"; note="$note pyodbc stubbed (unixodbc not installed);"
    else note="$note import failed: $(tail -1 "$O/imp-$L-$svc.log" | cut -c1-90);"; fi
  else note="pip install failed: $(grep -m1 -i error "$O/pip-$L-$svc.log" | cut -c1-100)"; fi
  echo "[$L] $svc: $(grep -c "^$svc " "$TK")/3 checks ok;$note"; rm -rf "$O/sv-$svc"
done
EOF
cat > "$B/fe_gate.sh" <<'EOF'
#!/bin/bash
# usage: fe_gate.sh <tree> <label>
# The frontend gate, run inside node:24-alpine (the Dockerfile's image). Tokens go to $(dirname <tree>)/tokens-fe-<label>.txt and the sorted
# TypeScript error list to tsc-<label>.txt. Restores what the builds rewrite (committed bundles, new .js.map files).
T=$1; L=$2; O=$(dirname "$T"); FE=$T/frontend_service; TK=$O/tokens-fe-$L.txt; : > "$TK"
rm -rf "$FE/node_modules"
docker run --rm -v "$FE":/app -w /app node:24-alpine sh -c '
  npm ci >/app/.g-ci.log 2>&1; echo "install $?" >/app/.g-rc
  npm test >/app/.g-test.log 2>&1; echo "tests $?" >>/app/.g-rc
  npm run typecheck >/app/.g-tsc.log 2>&1
  for m in ad-banner spending-chart spending-categories account-balance-trends; do npm run build:mfe:$m >/app/.g-$m.log 2>&1; echo "build-$m $?" >>/app/.g-rc; done
  npm run build >/app/.g-build.log 2>&1; echo "build-app $?" >>/app/.g-rc' >"$O/fe-docker-$L.log" 2>&1
[ -s "$FE/.g-rc" ] || echo "[$L] frontend: GATE DID NOT RUN (no result file; docker said: $(tail -2 "$O/fe-docker-$L.log" | tr '\n' ' ')). Re-run it alone, never alongside smoke.sh."
awk '$2==0{print "frontend " toupper($1) "=OK"}' "$FE/.g-rc" >> "$TK"
grep 'error TS' "$FE/.g-tsc.log" | sed -E 's/\([0-9,]+\)//' | sort -u > "$O/tsc-$L.txt"
echo "[$L] frontend: $(grep -c . "$TK")/7 checks ok; $(grep -E 'Tests ' "$FE/.g-test.log" | sed -E 's/\x1b\[[0-9;]*m//g' | tr -s ' '); $(wc -l < "$O/tsc-$L.txt") distinct TypeScript errors"
rm -f "$FE"/.g-*; rm -rf "$FE/node_modules"; git -C "$T" checkout -q -- frontend_service/public; git -C "$T" clean -fdq -- frontend_service/public
EOF
bash "$B/smoke.sh" "$WT" BASELINE | tee "$B/gate-baseline.log"
bash "$B/fe_gate.sh" "$WT" BASELINE | tee -a "$B/gate-baseline.log"
git -C "$WT" status --porcelain          # must print nothing before Phase A starts
```
Expect pre-existing results on a healthy `main` (2026-11-08, Apple Silicon Mac): `bill_pay`, `scenario_service`, `scheduler_service` and `transaction_service` import only with `pyodbc` stubbed because `unixodbc` is not installed (the script handles it, and says so); the frontend has **92 TypeScript error lines (56 distinct)**, 37 passing tests (5 files) and five green builds. These are the **pre-existing failures** the report lists so nobody blames the PR.

---

## Phase A — Agents

### Step 3: Resolve targets

```bash
cd "$WT"
# Current
awk -F== '/^newrelic==/{print $2}' accounts_service/requirements.txt auth_service/requirements.txt bill_pay/requirements.txt notifications_service/requirements.txt scheduler_service/requirements.txt transaction_service/requirements.txt | sort | uniq -c   # one value expected
grep -o 'nr-loader-spa-[0-9.]*[0-9]' frontend_service/app/nr.js | sort -u
# Python agent candidates: newest stable, then the next two
python3 -m pip index versions newrelic 2>/dev/null | sed -n 's/^Available versions: //p' | tr ',' '\n' | tr -d ' ' | grep -E '^[0-9]+(\.[0-9]+)*$' | head -3
# Report-only (never edited): nri-bundle vs its Terraform range, and the Dockerfile-pinned collectors
curl -sL https://helm-charts.newrelic.com/index.yaml | awk '/^  nri-bundle:/{f=1;next} f&&/^  [a-zA-Z]/{exit} f&&/^    version:/{print $2}' | sort -V | tail -1; grep -n 'version *=' terraform/aks/newrelic/nr_infra_agent.tf
gh api repos/open-telemetry/opentelemetry-collector-releases/releases/latest --jq .tag_name; gh api repos/open-telemetry/opentelemetry-java-contrib/releases/latest --jq .tag_name
grep -E '^ARG (OTEL_VERSION|JMX_SCRAPER_JAR_VERSION)' otel_collector_kafka/Dockerfile
```
Put the report-only findings in the report: a new nri-bundle **major** beyond `^8.0.0` is `NEEDS REVIEW` (a deliberate Terraform change plus the `ReliBank NR` workflow); collectors behind their latest release are listed, not edited. If the six `newrelic==` values differ, record it and still set all six to the same target.

### Step 4: Apply and verify

#### 4a. Python agent (the six exact-pinned services)

Try the candidates newest first. For each candidate `V`:
```bash
for s in accounts_service auth_service bill_pay notifications_service scheduler_service transaction_service; do
  V=$V perl -pi -e 's/^newrelic==.*/newrelic==$ENV{V}/' "$WT/$s/requirements.txt"      # no .bak file, so no `rm "$VAR/..."` (Claude Code's safety check blocks that form)
done
bash "$B/smoke.sh" "$WT" AGENT-$V accounts_service auth_service bill_pay notifications_service scheduler_service transaction_service
# regressions = tokens the baseline had for these services that this candidate lacks; empty output = accept the candidate
comm -13 <(sort "$B/tokens-py-AGENT-$V.txt") <(grep -E '^(accounts_service|auth_service|bill_pay|notifications_service|scheduler_service|transaction_service) ' "$B/tokens-py-BASELINE.txt" | sort)
```
Anything printed → `git -C "$WT" checkout -- <the six requirements.txt>` and try the next candidate. None pass → skip the Python agent and report each failure. `support_service` is not touched (its floor already installs the newest agent at build time; Step 8b records what runs).

#### 4b. Browser agent loader

Write and run the loader script. It prints `APPLIED old -> new`, `NO CHANGE`, or `HELD`.
```bash
cat > "$B/browser_loader.py" <<'PY'
import json, re, subprocess, sys

# usage: browser_loader.py <path to nr.js>      Upgrades the committed Browser agent loader to the newest published release.
path = sys.argv[1]
nr = open(path).read()
cur = re.search(r'nr-loader-spa-(\d+\.\d+\.\d+)\.min\.js', nr).group(1)
start = nr.find(';/*! For license information please see nr-loader-spa-')
prefix = nr[:start]                                     # NREUM.init / loader_config / info with the __PLACEHOLDER__ tokens; never changes

def fetch(v):                                           # curl, not urllib: the macOS python.org build has no root certificates
    r = subprocess.run(['curl', '-sfL', '--max-time', '60', f'https://js-agent.newrelic.com/nr-loader-spa-{v}.min.js'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 and r.stdout else None

def build(body):                                        # the one local edit nr.js carries: the register feature flag
    if body.count('feature_flags:[]') != 1: return None
    if re.search(r'__(ACCOUNT_ID|TRUST_KEY|APPLICATION_ID|LICENSE_KEY)__', body): return None   # the loader body must never contain a build placeholder
    return prefix + body.replace('feature_flags:[]', 'feature_flags:["register"]').rstrip() + '\n'

# Guard: the current file must be exactly reproducible from the published file of its own version. If not, someone edited nr.js
# by hand and swapping the body would silently drop that edit: hold instead.
base = fetch(cur)
if base is None or build(base) != nr:
    print(f'HELD: nr.js (loader {cur}) is not reproducible from the published loader + the register flag; not touching it'); sys.exit(2)

vers = json.loads(subprocess.run(['npm', 'view', '@newrelic/browser-agent', 'versions', '--json'], capture_output=True, text=True).stdout)
key = lambda v: tuple(int(x) for x in v.split('.'))
stable = sorted((v for v in vers if re.fullmatch(r'\d+\.\d+\.\d+', v) and key(v) > key(cur)), key=key, reverse=True)[:5]
for v in stable:
    body = fetch(v); out = build(body) if body else None
    if out:
        open(path, 'w').write(out); print(f'APPLIED {cur} -> {v}'); sys.exit(0)
print(f'NO CHANGE: {cur} is the newest published loader that applies cleanly' if not stable else f'HELD: newer loaders {stable} do not apply cleanly (missing or changed feature_flags)')
PY
python3 -I "$B/browser_loader.py" "$WT/frontend_service/app/nr.js"
```
On `APPLIED`, with the new version `N`:
1. Keep the unused npm declaration in step with it (cosmetic, no runtime effect): in `frontend_service`, `N=<new> perl -pi -e 's#("\@newrelic/browser-agent": ")[^"]+#$1^$ENV{N}#' package.json`, then regenerate the lock inside Node 24: `docker run --rm -v "$WT/frontend_service":/app -w /app node:24-alpine npm install --package-lock-only`. If the install fails, restore both files and leave the declaration alone.
2. Syntax check with dummy values, on a temporary copy (`node --check` needs a file path; verified 2026-11-08 on the `1.324.1` loader, and it fails on a broken file): `sed -e 's/__ACCOUNT_ID__/1/g' -e 's/__TRUST_KEY__/1/g' -e 's/__APPLICATION_ID__/1/g' -e 's/__LICENSE_KEY__/NRJS-1/g' "$WT/frontend_service/app/nr.js" > "$B/nr.check.js" && node --check "$B/nr.check.js"`; a failure restores the three files and reports `HELD`.
`HELD` or `NO CHANGE` → nothing to commit for the Browser agent.

### Step 5: Check and commit Phase A

```bash
cd "$WT"
git diff --name-only -- . ':!frontend_service' | grep -v -E '^(accounts_service|auth_service|bill_pay|notifications_service|scheduler_service|transaction_service)/requirements\.txt$'        # prints nothing, else `git checkout -- <file>` it and mention it
git diff --name-only -- frontend_service | grep -v -E '^frontend_service/(app/nr\.js|package\.json|package-lock\.json)$'                                                                # same
git diff -U0 -- frontend_service/package.json | grep -E '^[-+]' | grep -v -E 'browser-agent|^(\+\+\+|---)'                                                                                # prints nothing
```
Two commits, staging **named files only**:
```bash
git add accounts_service/requirements.txt auth_service/requirements.txt bill_pay/requirements.txt notifications_service/requirements.txt scheduler_service/requirements.txt transaction_service/requirements.txt
git commit -m "chore: new relic python agent upgrade $(date +%Y-%m-%d)" -m "newrelic <old> -> <new> in accounts, auth, bill_pay, notifications, scheduler, transaction"
git add frontend_service/app/nr.js frontend_service/package.json frontend_service/package-lock.json
git commit -m "chore: new relic browser agent upgrade $(date +%Y-%m-%d)" -m "nr-loader-spa <old> -> <new> (register feature flag kept)"
```
No diff → no commit; continue to Phase B (or finish).

---

## Phase B — Packages

Record each Python service's agent line now (post-Phase-A); it must be identical when Phase B ends.

### Step 6: Update, one unit at a time

#### 6a. Python (nine `requirements.txt`; `support_service` with its AI family)

```bash
$(command -v python3.12 || command -v python3) -m venv "$B/pvenv" && "$B/pvenv/bin/pip" install -q pur
cat > "$B/py_update.sh" <<'EOF'
#!/bin/bash
# usage: B=<scratch dir containing pvenv> py_update.sh <service dir> [family,csv]
# Raises the requirements.txt floors to the newest stable releases and keeps only what still resolves on Python 3.12.
# Prints APPLIED / HELD lines and the OLD/NEW diff; exit 1 (file restored) if the final file does not resolve.
cd "$1" || exit 2; FAM=${2:-}; : "${B:?}"
RES() { "$B/pvenv/bin/pip" install --dry-run --ignore-installed -q -r requirements.txt >"$B/res.log" 2>&1; }
WHY() { grep -m1 -E 'ERROR|conflict' "$B/res.log" | cut -c1-140; }
PUR() { "$B/pvenv/bin/python" -m pur -r requirements.txt --skip newrelic "$@" >/dev/null 2>&1; }
cp requirements.txt "$B/req.orig"
PUR                                                                   # 1) bulk: caps are kept, pre-release floors become stable
if RES; then echo "BULK OK"; else
  echo "BULK FAILED: $(WHY)"; cp "$B/req.orig" requirements.txt       # 2) one unit at a time; a unit is one package, or the whole family
  UNITS=$(python3 -I - requirements.txt "$FAM" <<'PY'
import re, sys
fam = {f.lower() for f in sys.argv[2].split(',') if f}
names = [m.group(1) for l in open(sys.argv[1]) if (m := re.match(r'([A-Za-z0-9_.-]+)(\[[^\]]*\])?\s*(==|>=|~=|<=|<|>)', l)) and m.group(1).lower() != 'newrelic']
inf = [n for n in names if n.lower() in fam]
print('\n'.join(([','.join(inf)] if inf else []) + [n for n in names if n not in inf]))
PY
)
  for unit in $UNITS; do
    cp requirements.txt "$B/req.try"; PUR --only "$unit"
    cmp -s requirements.txt "$B/req.try" && continue                  # already newest
    if RES; then echo "APPLIED $unit"; else cp "$B/req.try" requirements.txt; echo "HELD $unit: $(WHY)"; fi
  done
fi
RES || { cp "$B/req.orig" requirements.txt; echo "REVERTED: the final file does not resolve: $(WHY)"; exit 1; }
diff "$B/req.orig" requirements.txt | grep -E '^[<>]' | sed 's/^< /OLD /; s/^> /NEW /'
EOF
for s in accounts_service auth_service bill_pay notifications_service risk_assessment_service scenario_service scheduler_service transaction_service; do echo "== $s"; B=$B bash "$B/py_update.sh" "$WT/$s"; done
echo "== support_service"; B=$B bash "$B/py_update.sh" "$WT/support_service" "openai,langgraph,langchain,langchain-core,langchain-openai"
```
(Verified 2026-11-08 on copies of `main`: the bulk update resolves for all nine; a simulated conflict in `langchain-core` holds the whole AI family and still applies `fastapi`, `uvicorn` and `pydantic`; `newrelic` and the `gunicorn<24` cap are never touched. `exit 1` restores that file — record the service as `BREAKING — blocked` with the `REVERTED` line.)

Every `HELD` line goes in the report with its reason. Flag as `BREAKING RISK — included` every NEW floor whose major differs from the OLD one (e.g. `openai` 1 → 3, `kubernetes` 30 → 37). All nine are processed even when nothing moves. The result of a floor change is judged by Step 8, not here.

#### 6b. Frontend (npm, inside Node 24)

```bash
FE="$WT/frontend_service"; dk() { docker run --rm -v "$FE":/app -w /app node:24-alpine sh -c "$1"; }
cd "$FE"
dk 'npx --yes npm-check-updates --target latest --jsonUpgraded' > "$B/ncu-latest.json"      # newest incl. majors: only to list what is HELD
dk 'npx --yes npm-check-updates --target minor --reject @newrelic/browser-agent -u'
if ! dk 'npm install'; then
  # 1) the router family ERESOLVEs against the old lock: regenerate the lock from the updated package.json
  git checkout -- package-lock.json; rm -f package-lock.json; rm -rf node_modules
  if ! dk 'npm install'; then
    # 2) hold the router family and retry against the original lock
    git checkout -- package.json package-lock.json
    dk "npx --yes npm-check-updates --target minor --reject '@newrelic/browser-agent,react-router,react-router-dom,@react-router/*' -u"
    dk 'npm install' || { git checkout -- package.json package-lock.json; echo "frontend: REVERTED, npm install fails"; }
  fi
fi
rm -rf node_modules; git diff -U0 -- package.json | grep -E '^[-+].*@newrelic/'      # must print nothing
git status --short                                                                    # only package.json / package-lock.json
```
Verified 2026-11-08: `--target minor` moved 20 packages (react 19.2 → 19.3, react-router 7.18.2 → 7.18.5, vitest, vite 6.4.5, jest-dom 6.9.1 → 6.10.0, …); `npm install` failed with `ERESOLVE` on the router family; regenerating the lock (rung 1) installed, and the gate still passed (37/37 tests, no new TypeScript errors, five green builds). The lock changes by ~3,000 lines when regenerated — say so in the report. Record the kept bumps, the `HELD` majors from `ncu-latest.json`, and which fallback was used. Revert the frontend (`git checkout -- package.json package-lock.json`) if no variant installs, or the `@newrelic/` check prints anything.

**Deprecation check (do not skip; a green gate does not catch this).** Read the install log for packages this run raised: `grep 'npm warn deprecated' "$B/npm-install-"*.log`. A bumped package that npm marks deprecated is held at the version it had (rung 2: newest compatible): set it back in `package.json`, run `docker run --rm -v "$FE":/app -w /app node:24-alpine npm install --package-lock-only`, and list it `HELD` with npm's own message. Found on the first real run (2026-11-08): `@testing-library/jest-dom` 6.10.0, "Incorrect minor release with breaking changes ... Use 6.9.1 for the 6.x line"; the 37 tests still passed, which is why it needs this explicit check. Fold the revert into the Phase B commit before Step 8 (`git commit --amend`: the branch is local and unpushed).

### Step 7: Check and commit Phase B

```bash
cd "$WT"
git status --porcelain | grep -v -E '^ M (accounts_service|auth_service|bill_pay|notifications_service|risk_assessment_service|scenario_service|scheduler_service|support_service|transaction_service)/requirements\.txt$|^ M frontend_service/package(-lock)?\.json$'    # prints nothing, else revert/clean it and mention it
git diff -U0 -- . ':!frontend_service/package-lock.json' | grep -E '^[-+]newrelic==|nr-loader-spa|@newrelic/browser-agent'                                               # must print nothing: no agent version moved
```
If a diff remains:
```bash
git add accounts_service/requirements.txt auth_service/requirements.txt bill_pay/requirements.txt notifications_service/requirements.txt risk_assessment_service/requirements.txt scenario_service/requirements.txt scheduler_service/requirements.txt support_service/requirements.txt transaction_service/requirements.txt frontend_service/package.json frontend_service/package-lock.json
git commit -m "chore: package and library updates $(date +%Y-%m-%d)" -m "<one line per service or frontend: what moved, what is HELD and why, any code adaptation>"
```
(`git add` of an unchanged file is harmless; the check above already proved nothing else is modified.)

---

## Application gate

### Step 8: Prove the application still works

The per-unit checks rejected anything that failed to resolve. This step proves the **whole application** behaves as on baseline. Run it once on the final tree, for the phases in scope.

Run the two gates **one after the other** (background is fine, but not both at once). On the first real run (2026-11-08) a frontend gate started alongside `smoke.sh` returned nothing at all (0/7, no test output) and did not reproduce when re-run alone (7/7); the cause was not established, so the skill avoids the overlap. A `GATE DID NOT RUN` line means re-run it alone, not that the packages are broken.

```bash
bash "$B/smoke.sh" "$WT" AFTER | tee "$B/gate-after.log"
bash "$B/fe_gate.sh" "$WT" AFTER | tee -a "$B/gate-after.log"
# Regressions = tokens the baseline had and the final tree lacks, plus any TypeScript error that is new
comm -13 <(cat "$B"/tokens-py-AFTER.txt "$B"/tokens-fe-AFTER.txt | sort) <(cat "$B"/tokens-py-BASELINE.txt "$B"/tokens-fe-BASELINE.txt | sort)
comm -13 "$B/tsc-BASELINE.txt" "$B/tsc-AFTER.txt"
git -C "$WT" status --porcelain          # must print nothing
# What actually changed in what runs: the installed set before -> after, per service
for s in accounts_service auth_service bill_pay notifications_service risk_assessment_service scenario_service scheduler_service support_service transaction_service; do echo "== $s"; diff "$B/freeze-BASELINE-$s.txt" "$B/freeze-AFTER-$s.txt" | grep -E '^[<>]'; done
```
Anything either `comm` prints is a **regression**; a check that already failed on baseline is a *pre-existing failure*. The last loop is the real before/after for the report (for an unchanged-floor service it is empty or just the agent line).

**On a regression** (deterministic — no questions):
1. Map it to its unit (token prefix → service; `frontend` → the frontend and, for a build/test token, possibly the Browser loader).
2. Restore the unit to baseline and commit the restore:
   ```bash
   FILES=$(git diff --name-only origin/main HEAD -- <the unit's files>)
   git checkout origin/main -- $FILES
   git commit -m "revert: <unit> maintenance changes (application gate regression: <check>)"
   ```
   Restore Phase B files first; if the same token still fails, restore the Phase A files too (the whole Python agent unit, all six services, or the Browser loader). Record it under **BREAKING — blocked** with the failing check's evidence line.
3. Re-run Step 8. Still failing → the cause is not that unit: mark the branch **NOT READY**, keep the worktree, and report the failing check with `WT` and `BRANCH` (see Step 9).

#### Code adaptation (rung 3, at most once per unit)
If a bump fails only because the package renamed or removed an API the service's own code uses, and the package's changelog names the replacement, make the smallest change that restores the old behavior: at most 10 changed lines per service, in that service's own application file, never in a file the "planted demo behavior" rule protects. Re-run that service's smoke check and the whole Step 8. Commit it on its own as `chore: adapt <service> to <package> <version>` and list it under `NEEDS REVIEW — CODE CHANGE`. Anything bigger is rung 4: hold the package.

### Step 8b: Validate in New Relic — local deploy against the production baseline

Runs after Step 8 passes, for every scope that changed code. It deploys the finished branch to the local `docker-desktop` cluster (never any other), runs the repo's own tests as traffic, and compares the data in the **Local** account with the Step 0 baseline. It also builds the real Docker images, which Step 8 cannot. **Skip it — never ask — and say why, prominently, in the report** when: Step 0 recorded NO BASELINE; `docker info` does not answer within 10 s; the repo's `skaffold.env` is missing; or any guard below fails.

**When Step 8b is skipped, run the image check instead** (docker only, no cluster, no secrets passed, nothing deployed): build the images whose runtime changed — the six agent services plus `scenario-runner` when its `httpx` pin moved — with the Dockerfile and context from `skaffold.yaml`, then run in each image `python -c "import newrelic, <app module>"` and `pip check` (this exercises the real ODBC driver that the host check in Step 8 has to stub). Tokens `<image> BUILD/RUN/PIPCHECK` go in the report as the substitute evidence, labelled as such: it proves the images build and import, not that telemetry reaches New Relic. Remove the `maint-check/*` tags afterwards. A leftover deployment on `docker-desktop` is not a reason to skip: it is taken down first (see "Take down an old deployment" below).

**Guards.** The person's kubeconfig also holds production clusters and its current context is usually one of them, so build a one-context kubeconfig from the `docker-desktop` entry (this reads the config and switches nothing; verified 2026-11-08 with an EKS context current) and never touch the default one again:
```bash
K="$NR/kubeconfig"
kubectl config view --raw --flatten -o json | python3 -I -c '
import json, sys
c = json.load(sys.stdin)
ctx = next(x for x in c["contexts"] if x["name"] == "docker-desktop")["context"]      # no such context: skip Step 8b
out = {"apiVersion": "v1", "kind": "Config", "current-context": "docker-desktop",
       "clusters": [x for x in c["clusters"] if x["name"] == ctx["cluster"]],
       "users": [x for x in c["users"] if x["name"] == ctx["user"]],
       "contexts": [{"name": "docker-desktop", "context": ctx}]}
json.dump(out, open(sys.argv[1], "w"))' "$K" && chmod 600 "$K"; export KUBECONFIG="$K"
[ "$(kubectl config get-contexts -o name | tr -d '\n')" = docker-desktop ] || echo "SKIP: kubeconfig is not single-context"
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'      # must be https://127.0.0.1:… or localhost
ACC=$(grep -E '^NEW_RELIC_ACCOUNT_ID=' "$REPO/skaffold.env" | cut -d= -f2 | tr -d '"')   # must equal the id of "Demogorgon Local" and differ from "Demogorgon Prod"
APP_NAME=$(grep -E '^APP_NAME=' "$REPO/skaffold.env" | cut -d= -f2- | tr -d '"')           # local app names are "<APP_NAME> - <Service>"
```
**Take down an old deployment** (do this whenever `relibank`, `chaos-mesh` or `newrelic` already exists; no question, no skip). Written from the first real run (2026-11-08), where the old deployment was mostly `ImagePullBackOff` and had releases named `chaos-mesh`, `newrelic-nri-bundle` and `nri-bundle` (not the `nri-bundle-local-dev` that skaffold installs). Order matters:
```bash
export KUBECONFIG="$NR/kubeconfig"; [ "$(kubectl config get-contexts -o name | tr -d '\n')" = docker-desktop ] || exit 1
{ for ns in relibank chaos-mesh newrelic; do echo "== $ns"; kubectl get deploy,sts,ds,job,svc,pvc -n $ns -o name 2>/dev/null; done; helm list -A; } > "$NR/old-deployment.txt"      # a record for the report
# 1) helm releases first (not the namespaces): that also removes their cluster-wide webhooks and cluster roles. List them, then one explicit command each (zsh does not word-split a loop variable).
helm list -A -o json | python3 -I -c 'import json,sys; [print(r["name"], r["namespace"]) for r in json.load(sys.stdin) if r["namespace"] in ("relibank","chaos-mesh","newrelic")]'
helm uninstall <name> -n <namespace> --wait --timeout 3m          # once per line printed above
# 2) the manifests skaffold owns, from $WT (errors about releases that do not exist are expected)
(cd "$WT" && SKAFFOLD_UPDATE_CHECK=false skaffold delete -p local)
# 3) the namespaces
kubectl delete ns relibank chaos-mesh newrelic --wait=true --timeout=300s
# 4) if `relibank` is stuck Terminating, the Chaos Mesh PodChaos objects still carry a finalizer that only the (now removed) controller could clear; clear it on those objects only
for n in $(kubectl get podchaos.chaos-mesh.org -n relibank -o name 2>/dev/null); do kubectl patch "$n" -n relibank --type=merge -p '{"metadata":{"finalizers":null}}'; done
# 5) verify: no helm releases, the three namespaces gone, no leftover chaos/newrelic webhook configs
helm list -A; kubectl get ns -o name; kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations -o name | grep -i -E 'chaos|nri|newrelic'
kubectl get ns -o name > "$NR/ns-before.txt"
```
The Chaos Mesh CRDs stay (cluster-wide, and `helm install` accepts existing ones); a later install reuses them. If a step still fails after one retry, report `NOT VALIDATED — environmental` and say which step.
Copy `$REPO/skaffold.env` into `$WT` (`chmod 600`; it is git-ignored and absent from the worktree; never print it), then create the generated file the build hook would otherwise skip on a cache hit: `bash "$WT/scripts/generate-nrdot-env.sh"`. The worktree removal in Step 9 deletes both.

**Deploy.** From `$WT`, in the background (the first build is slow: mssql, kafka and the NRDOT collector images are amd64 and run emulated on Apple Silicon; later runs hit the cache):
```bash
T0=$(date +%s)
SKAFFOLD_UPDATE_CHECK=false skaffold run -p local --tail=false --status-check=true > "$NR/skaffold.log" 2>&1
```
- It builds 15 images, installs two helm releases (`chaos-mesh`, `nri-bundle-local-dev`, the latter always the **newest** nri-bundle chart: a free check of the chart the Terraform range will float to), then applies the Kustomize `dev` overlay and waits for the deployments. An image that fails to build is a regression: restore that service as in Step 8 and report it `BREAKING — blocked`. A failure outside this branch (helm repo or registry unreachable, Docker out of disk) is `NOT VALIDATED — environmental`: tear down and say so.
- Skaffold's after-deploy hook **applies the Chaos Mesh experiments** from `scenario_service/chaos_mesh/experiments/relibank-pod-chaos-examples.yaml` (pod-kill / pod-failure on transaction, accounts, bill-pay, scheduler and messaging, 45 s – 2 min each). Pods restarting in the first minutes are therefore expected and not the branch's doing. Wait 180 s after `skaffold run` returns (use a `Monitor` until-loop on `date +%s`, not a foreground sleep), then require `kubectl get pods -n relibank --no-headers | awk '$3!="Running" && $3!="Completed"'` to print nothing, and record every pod's restart count as the reference (`kubectl get pods -n relibank --no-headers | awk '{print $1, $4}' > "$NR/restarts-ref.txt"`).

**Traffic and tests.** There is no load generator; the repo's own suite is the traffic. Port-forward the services (the ports `skaffold.yaml` lists), then run the tests from `$WT/tests` against `localhost`:
```bash
for m in frontend-service:3000:3000 accounts-service:5002:5002 auth-service:5006:5002 bill-pay-service:5000:5000 support-service:5003:5003 transaction-service:5001:5001; do
  IFS=: read -r svc lp sp <<< "$m"; nohup kubectl port-forward -n relibank "svc/$svc" "$lp:$sp" > "$NR/pf-$svc.log" 2>&1 & echo $! >> "$NR/pf.pids"
done
python3.12 -m venv "$NR/tv" && "$NR/tv/bin/pip" install -q pytest pytest-timeout requests selenium
cd "$WT/tests"
# 1) functional pass: end-to-end flows across frontend, auth, accounts, bill pay, support
"$NR/tv/bin/python" -m pytest test_end_to_end.py -rA --tb=line -p no:cacheprovider --timeout=300 > "$NR/e2e-1.log" 2>&1
# 2) steady load: the same suite again and again for 6 minutes
end=$(( $(date +%s) + 360 )); while [ "$(date +%s)" -lt "$end" ]; do "$NR/tv/bin/python" -m pytest test_end_to_end.py -q -p no:cacheprovider --timeout=300 >> "$NR/e2e-load.log" 2>&1; done
# 3) the tests that read New Relic (they load NR credentials from the worktree's skaffold.env)
"$NR/tv/bin/python" -m pytest test_newrelic_instrumentation.py -rA --tb=line -p no:cacheprovider --timeout=600 > "$NR/nr-instr.log" 2>&1
# only when AZURE_OPENAI_API_KEY is set in skaffold.env (it was empty on 2026-11-08, so the AI flow cannot run locally: report NOT AVAILABLE)
# "$NR/tv/bin/python" -m pytest test_newrelic_ai_agents.py -rA --tb=line -p no:cacheprovider --timeout=600 > "$NR/nr-ai.log" 2>&1
# only when /Applications/Google Chrome.app exists: the Browser agent and the microfrontend timing (exercises the new nr.js loader)
"$NR/tv/bin/python" -m pytest test_browser_user_tracking.py test_microfrontend_telemetry.py -rA --tb=line -p no:cacheprovider --timeout=900 > "$NR/browser.log" 2>&1
```
Then `kubectl get pods -n relibank` again and compare restarts with `restarts-ref.txt`, and wait **150 seconds** for ingestion before querying.

**Failures in the tests.** A failing test is a regression until a control run says otherwise. Tear down (below), then deploy `origin/main` the same way from a second worktree and run only the failing tests. Failing on both → *pre-existing* (list it). Failing only on the branch → restore the unit the test maps to (service by name or port) as in Step 8, deploy again once and re-run; still failing → `NOT READY`.

**Compare** (MCP, account `Demogorgon Local`; every query `SINCE <T0>`). First list the local names: `SELECT uniques(appName) FROM Transaction WHERE appName LIKE '<APP_NAME> - %' SINCE <T0>`, then re-run Step 0 rows 1–9 and 11 with those exact names (match prod by the suffix after ` - `) and apply:

| Check | PASS when | If not |
|---|---|---|
| Every APM service reports transactions, APM metrics, logs and spans | all 7 suffixes present | a missing service is `BREAKING — blocked` |
| Agent version | in each pod `kubectl exec -n relibank deploy/<svc> -- pip show newrelic` equals the Phase A target for the six, and shows what `support_service` actually runs (report it; its floor is not edited); the entity tag `agentVersion` is shown beside it, informational | `BREAKING — blocked` |
| Golden signals | Apdex, rpm, average and p95 present; per service, local p95 not above prod's by more than 25% and error rate not above prod's by more than 8 points (one-sided: prod carries scheduled fault injection) | `NEEDS REVIEW` |
| Error classes | every `error.class` / `error.message` seen locally also appears in prod's 24 h list | a new class is `NEEDS REVIEW` |
| Traces | traces exist for every service; average services per trace within ±1 of prod's | `NEEDS REVIEW` |
| Logs | each service has logs; trace-linked share within 15 points of prod's | `NEEDS REVIEW` |
| Datastores | Postgres (accounts) and MSSQL (transaction, bill pay) spans present wherever prod has them | `NEEDS REVIEW` |
| Saturation | `K8sContainerSample` for `clusterName = 'relibank-dev'`, `namespaceName = 'relibank'`: max memory per deployment not above 2× prod's `maxMemMB`; CPU shown beside prod's, not compared (the load differs) | `NEEDS REVIEW` |
| Pods | all `Running`/`Completed`; restarts did not increase after the reference taken once the Chaos Mesh experiments had ended | `BREAKING — blocked` |
| Integrations | `PostgresqlDatabaseSample` and the `sqlserver.*` / `kafka.*` metrics present locally if present in prod | informational |
| Browser | applicable when `NEW_RELIC_BROWSER_APPLICATION_ID` is set and Chrome is installed: `PageView` and `MicroFrontEndTiming` from the local Browser app after the Selenium tests; if Phase A moved the loader, `uniques(agentVersion)` on `PageView` equals it. No `PageView` at all with the new loader → restore the Browser commit's files as in Step 8 (`BREAKING — blocked`); otherwise `NOT APPLICABLE` | `NEEDS REVIEW` |
| Tests | `test_end_to_end.py` and `test_newrelic_instrumentation.py` pass, or fail identically on the `main` control run | see above |

**Tear down** (always, even after a failure): kill the port-forwards in `$NR/pf.pids`; `skaffold delete -p local` from `$WT`; delete the three namespaces (`kubectl delete ns relibank chaos-mesh newrelic --ignore-not-found --wait=true --timeout=300s`, which also drops the PVCs; clear the PodChaos finalizers as in the take-down step if `relibank` hangs in Terminating); confirm `kubectl get ns -o name` equals `$NR/ns-before.txt` (taken after the old deployment was removed, so nothing of the old one comes back). Never touch other namespaces or any other cluster. Save the tables to `$NR/local-validation.md`.

---

## Finish

### Step 9: Finish locally (nothing is pushed)

Same for every scope. The skill never pushes: the branch and its commits stay in the user's local repository until the user runs the push command from the report.

- **Gate still failing after the restore** → keep the worktree and the branch, print **no** push command, and mark the report **NOT READY — do not push** with the failing check, `WT` and `BRANCH`.
- **No commits on the branch** → `cd "$REPO" && git worktree remove --force "$WT" && git branch -D "$BRANCH"`, report "nothing to upgrade" or why every unit failed. Stop.
- **Otherwise:**
  ```bash
  git -C "$WT" status --porcelain          # must print nothing (tracked changes all committed)
  git -C "$WT" log --oneline --first-parent origin/main..HEAD
  cd "$REPO" && git worktree remove --force "$WT"      # --force only discards ignored files (skaffold.env, nrdot-mssql.env, node_modules); the branch and its commits stay in the user's local repo
  git rev-parse --verify --quiet "refs/heads/$BRANCH"  # must print a SHA: the local branch survived
  ```
  Do **not** run `git push`. If `status --porcelain` prints anything, commit it per the allow-list (or revert it) before removing the worktree.

### Step 10: Final report

Print this and stop — it is the only output the user needs. **Start with the breaking-change section, even when it is empty ("None found").**

1. **BREAKING CHANGES** — four lists:
   - **BREAKING — blocked.** Excluded from the branch because it failed to install, build, test or start; the application would have broken. One evidence line each, e.g. "Python agent 14.2.0: `pip install` fails in `transaction_service`: …", "frontend `react-router` 7.18.5: `ERESOLVE` against the old lock", plus any unit restored by the application gate or Step 8b.
   - **BREAKING RISK — included.** Passed every check but can change behavior: the Python agent major (13 → 14), every Python floor whose major rose, `0.x` bumps, a raised base image, and any Browser loader jump. Each says "read the release notes".
   - **HELD.** Not a failure: a cap, pin or conflict kept it out (the `gunicorn<24` cap; npm majors with their versions; a Python unit that would not resolve; nri-bundle or a collector behind its latest release).
   - **NEEDS REVIEW.** A person must look: every code adaptation, every Step 8b check that did not PASS, anything unexplained (say so plainly), a new nri-bundle major, and everything that could not be verified here (Browser without Chrome, the AI flow without Azure OpenAI credentials, a skipped Step 8b).
2. **Application gate** (Step 8): check | baseline | after for each Python service (install, `pip check`, import), the frontend (install, 37 tests, five builds, TypeScript error count), and the Browser loader checks; then the **pre-existing failures** (identical on baseline) so nobody blames this PR. Then **what actually changed in what runs**: the installed-set diff per service (Step 8's last loop), stated plainly as "unchanged — floors only" where it is.
2b. **Telemetry validation** (Step 8b): the production baseline beside the local numbers — agent versions (prod | branch | local pod), golden signals per service, APM metrics, logs with trace-linked share, trace depth, error classes, datastores, saturation, pods and restarts, Browser, integrations — each row PASS / REVIEW / NOT AVAILABLE with the reason. Say plainly that local numbers come from ~10 minutes of the repo's own tests against 24 hours of production.
3. **Commit 1 — Python agent** (SHA): `newrelic` old → new in six services. **Commit 2 — Browser agent** (SHA): loader old → new.
4. **Commit 3 — Packages** (SHA): per service, the floors that moved (old → new), plus the frontend table (what it was / what it is now), the `HELD` majors, and whether the lock was regenerated.
5. **Report-only**: nri-bundle current range vs newest chart, collector versions vs their latest release, base images.
6. **Other decisions**: every unit skipped or downgraded from "latest" that is not covered above (e.g. "support_service newrelic floor not edited: runs X.Y.Z").
7. **Flags**: runtimes that didn't match a Dockerfile, skipped verification, and every open PR from the collision check.
8. **Branch (local only — nothing was pushed)**: the name, `git switch <BRANCH>` to review it, and the command for the user to run once satisfied: `git push -u origin <BRANCH>`, plus the compare link `https://github.com/newrelic/relibank/compare/main...<BRANCH>?expand=1` (it works only after the push). When the gate failed, print neither.
9. **Ready-to-paste PR**: title `chore: maintenance YYYY-MM-DD` (or the single-phase commit message), and a body that fills `.github/PULL_REQUEST_TEMPLATE.md` — keep every heading and checkbox line exactly, fill each section briefly, put agent/package upgrades in tables (what it was / what it is now), open with the BREAKING section, tick only boxes that are verified facts — and the sentence *"Review commit by commit. If sandbox breaks, deploy the first commit's SHA to tell an agent problem from a package problem; `git revert <sha>` removes one."* (The `fill-pr` skill can build the body once the branch is pushed.)
10. **Not done by this skill**: pushing the branch, opening the PR, the deployed-environment tests below, and the Terraform-managed pieces. Name the files saved in `$NR` (`baseline-prod.md`, `local-validation.md`) so the person can keep them; they live in a temp directory.

---

## After the PR is opened (manual — this skill does none of it)

1. Run **Deploy ReliBank** (`deploy-relibank.yml`): `action_type` = `deploy`, `environment` = `sandbox`, `target_color` = the color you are validating (typically the one not serving traffic), `force_rebuild` = **true** (the manifests have no lock, so a source-hash cache hit would reuse an old resolve), `assistant_b_delay_seconds` = the default `0`.
2. Run **Relibank Test Suite** (`test-suite.yml`, `workflow_dispatch`): `target_environment` = `sandbox`, `test_suite` = `all`, `target_color` = that color. It needs a live environment, so this skill cannot run it. The scheduled run (daily 13:00 UTC) targets **prod** and says nothing about this branch until it is deployed there.
3. Production only after sandbox sign-off (same two workflows, `environment` = `prod`).
4. A new nri-bundle major, if the report flagged one, goes through `ReliBank NR` (`relibank-newrelic.yml`) as its own change.

### Validation checklist
- **Pods**: `kubectl get pods -n relibank-<color>` — all Running, RESTARTS = 0; `kubectl get pods -n newrelic` for the New Relic pods.
- **Agent versions**: `kubectl exec -n relibank-<color> deploy/<service> -- pip show newrelic` for the six services and for `support_service`; APM & Services → service → "Agent version". During a blue/green rollout the entity-level tag can blend both colors; compare with `Transaction` faceted by `appName, deploy.color` instead. Browser: `SELECT uniques(agentVersion) FROM PageView WHERE appName = '<Browser app>'` should show the new loader.
- **Observability** for every touched service: APM graphs (web transactions, throughput, error rate), Distributed Tracing complete end to end, Logs with current timestamps, Infrastructure (no CPU/memory spike), Database tables, and Browser metrics (including the microfrontend timing). A small gap during the rolling update is normal; more than 5 minutes after restart means collection is broken.
- **Regression**: the manual **Relibank Test Suite** run in step 2 above is green.

## Rollback

1. Re-deploy `main` to sandbox: **Deploy ReliBank** with `main`, `action_type` = `deploy`, `environment` = `sandbox`.
2. Find the culprit commit by deploying the Phase A commit alone, then the Browser commit.
3. `git revert <sha>` that commit (agents, Browser and packages are separate, so the others survive), push, redeploy, revalidate.
4. If one library is at fault, set it back to its previous floor in the manifest instead of reverting the whole commit; if the cause is a fresh upstream release rather than this PR, add a cap (`<X`) with a comment.

## Known Issues & Tribal Knowledge

- **Authoring status (2026-11-08).** Written from the demogorgon `maintenance` skill and checked on a throwaway copy of `origin/main` (`3fe6ab3`): the nine Python manifests resolve on 3.12 before and after a bulk floor bump; the six services resolve with `newrelic==14.2.0`; the install/`pip check`/import smoke and the frontend gate run and give the baselines quoted above; the `ncu` update and both lock fallbacks run in Node 24; the Browser loader script reproduces `1.312.1` exactly, upgrades it to `1.324.1` on a copy (the result passes `node --check`), is a no-op on a second run and holds on a tampered file; the one-context kubeconfig builds from the `docker-desktop` entry while an EKS context is current; the four scripts embedded in this file pass `bash -n` / `py_compile` and were re-run after extraction. **First real run (2026-11-08, `/maintenance`, no scope):** Step 0 ran against `Demogorgon Prod` (4120837: seven APM apps plus a `Notifications Function` app that is not a pod service; prod agent tags 13.4.0 for six, 13.6.1 for support) and the baseline held; Steps 1–8 ran to completion and produced three commits (Python agent 13.4.0 → 14.2.0, Browser loader 1.312.1 → 1.324.1, packages); the application gate was 27/27 Python and 7/7 frontend (37 tests, 56 TypeScript errors, none new); seven changed images were built from the real Dockerfiles and imported cleanly in-image. Fixes made from that run are in this file: the depth query's `SINCE`, `perl -pi` instead of `sed -i.bak` + `rm`, the silent frontend gate, the npm deprecation check (caught `jest-dom` 6.10.0), running the gates one after the other, and the image-check fallback. **Step 8b then ran end to end** after the person granted full control of `docker-desktop` (an old deployment was taken down with the "Take down an old deployment" procedure below). It needed eight `skaffold run` attempts, all for environment reasons listed in the next section, not for anything in the branch; once through, 17 of 18 pods ran, the repo tests and Browser agent were exercised, six of seven services reported telemetry on agent 14.2.0, and the cluster was returned to its clean state. **Still not exercised:** the control run on `main` (every failing test was instead traced to a cause in the services' own logs), and Transaction Service telemetry (SQL Server cannot stay up on this Mac).
- **Step 8b environment problems seen on the first real run (2026-11-08, Apple Silicon Mac, Cloudflare Gateway network).** None came from the branch; each has a worktree-only workaround (never committed, discarded with the worktree) and goes in the report as an environment note:
  - **GitHub `releases/download/...` returned 504** for every file while `api.github.com` worked (headers were GitHub's own). It broke three things: the two `ADD https://github.com/...` lines in `otel_collector_kafka/Dockerfile`, the `curl` of the NRDOT `.deb` in `otel_collector_mssql/Dockerfile`, and skaffold's fetch of the `nri-bundle` chart. Workaround: `gh release download <tag> -R <repo> -p <asset> -D <context dir>` (API route), **verify size and `sha256` against `gh api repos/<repo>/releases/tags/<tag> --jq '.assets[]|{name,size,digest}'`**, then `COPY` the file. skaffold cannot expand `${TARGETARCH}` in a `COPY` path, so use a fixed file name. For the chart: unpack the `.tgz`, point `chartPath:` at the directory and set `skipBuildDependencies: true` on that release.
  - **TLS interception.** The network re-signs HTTPS with "Gateway CA - Cloudflare Managed" (trusted by macOS, not by containers), so `curl https://repo.percona.com/...` inside `postgres-custom` failed with a certificate error. Workaround: export that public CA from the System keychain into the build context and `COPY` it to `/usr/local/share/ca-certificates/` before the `apt-get install` that pulls `ca-certificates` (`update-ca-certificates` does not exist yet in `postgres:15`).
  - **SQL Server crashes on this Mac** (x64 under what looks like QEMU: no Rosetta mount in Docker's VM). Reproduced outside Kubernetes with the unchanged `mssql-custom` image: `MSSQL_AGENT_ENABLED=true` and `MSSQL_ENABLE_HADR=1` each kill it within ~25 s, and with both off it still dies when the init script or the services connect. So `mssql-init`, Transaction Service (retries its login forever and never starts) and the MSSQL-backed flows cannot be validated here; report `NOT VALIDATED — environmental` and never edit the `k8s/base` memory limits. Fix on the machine: Docker Desktop → Settings → General → use Apple Virtualization framework with Rosetta for x86_64/amd64 emulation (not verified).
  - **`nrdot-collector-mssql`** cannot run: the manifest starts `nrdot-collector-host`, the newest NRDOT package ships only `nrdot-collector`, and the config uses components the newest release renamed (`newrelicsqlserver`, `deltatorate`, `metricsaslogs`); the Dockerfile's own comment records this drift. It is not caused by a branch. Scale it to 0 locally so it does not distort restart counts.
  - **`support-service` refuses to start without `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY`**, which `skaffold.env` does not define. `kubectl set env deploy/support-service ... =<placeholder>` lets it boot (proves the upgraded AI stack starts); every AI call then fails, which also fails the risk-assessment path (503) and the Alice/Bob payment tests. Stripe's key is a placeholder too (401). Those five `test_end_to_end.py` failures are environmental.
  - **The infrastructure agent's `nrk8s-kubelet` cannot start on `docker-desktop`** ("path / is mounted on / but it is not a shared or slave mount"), so there is no `K8sContainerSample`; the Saturation row is `NOT AVAILABLE`. The rest of `nri-bundle` 8.0.40 installs and runs, which is the free chart check.
  - **Background-only services (Notifications) lose the first transactions**: the Python agent connects on the first transaction and drops what happens before it is connected. Publish a first message, wait, then publish a spaced second batch (`kafka-console-producer.sh` needs `env JMX_PORT= KAFKA_JMX_OPTS=` to avoid a JMX port clash); only then is silence a real finding.
  - **Chaos Mesh PodChaos objects carry a `chaos-mesh/records` finalizer**: deleting the namespace after uninstalling the chart hangs; patch the finalizers to null on those objects.
  - `test_microfrontend_telemetry.py` does not read `skaffold.env` (export the three `NEW_RELIC_*` variables for it, without printing them) and its Selenium flow waits for dashboard elements that need Transaction Service; the Browser loader is verified instead by (a) the served page containing `nr-loader-spa-<new>` with no `__PLACEHOLDER__` left and (b) a headless-Chrome page load followed by `SELECT uniques(agentVersion) FROM PageView FACET appName`.
- Manifests are floors with no lock, so the resolved set changes between any two builds even without a PR. The Python phase moves floors to match; the before/after installed-set diff is the honest measure.
- `newrelic==13.4.0` was pinned in six services while `support_service` (floor `>=13.6.1`) already installed `14.2.0` at build time: the services ran two agent majors side by side.
- **Machine quirks (Apple Silicon Mac):** the python.org Python has no root certificates, so `urllib` fails on HTTPS (use `curl` or `pip`); `unixodbc` is not installed, so `pyodbc` cannot be imported (the smoke script stubs it and says so; `brew install unixodbc` removes the stub); the host Node 20.8 / npm 10.1 cannot run `ncu@latest` and crashes on installs (use Node 24 in Docker). `python3 -m pur` is installed on the host; the skill installs its own copy in `$B/pvenv`.
- `package.json` carries `"mui": "^0.0.1"` and an unused `@newrelic/browser-agent`; both are dead weight and left alone.
- The main pytest suite under `tests/` is written for deployed environments; only `test_end_to_end.py`, `test_newrelic_instrumentation.py` and the two Selenium files are used locally. The AI-agent test needs Azure OpenAI credentials (empty in the local `skaffold.env`), so `LlmAgent` / `LlmTool` monitoring cannot be validated locally.
- Skaffold facts: the `nrdot-mssql.env` file is generated by a build hook that is skipped on a cache hit (hence the explicit `generate-nrdot-env.sh` call); `skaffold run` reads `skaffold.env` from the directory it runs in; `skaffold dev` port-forwards, `skaffold run` does not (hence the explicit `kubectl port-forward`); the chaos experiments are applied after every deploy.
- Color: APM `Transaction` / `TransactionError` carry the deploy color in the custom attribute `deploy.color`, `Span` in `k8s.namespace.name` (`relibank-<color>`); `Log`, the MSSQL collector `Metric` and Browser events have no color dimension.
- Production's New Relic account also holds the Demogorgon and ReliFarm apps, and two AKS clusters have carried the name `relibank-prod`: filter by the `ReliBank (Prod) - ` prefix and prefer the cluster row with the newest data.
- `nr-ebpf-agent` is not a separate release: it rides along inside the `nri-bundle` chart.
- The IDE may flag `allowed-tools` in this file's frontmatter as an unsupported attribute; it is how this repo's skills declare their tools.

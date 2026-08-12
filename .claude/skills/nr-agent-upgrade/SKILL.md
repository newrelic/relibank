---
name: nr-agent-upgrade
description: Upgrade New Relic agents across ReliBank — nri-bundle (Helm/Terraform) and APM agents (Python per service, Node.js browser agent for frontend_service). Use when the user asks to upgrade New Relic agents, bump NR versions, or run the NR agent upgrade runbook.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Glob
  - Grep
---

# New Relic Agent Upgrade Skill

Upgrade New Relic agents across ReliBank. This skill makes the code changes. Deployment is always manual — the user triggers CI/CD pipelines.

**HARD RULE: Never trigger deployments, push to remote, or run `kubectl` / `helm` commands. Code changes only.**

## Escalation Contacts

| Notify / Escalate | Contact |
|---|---|
| @Gabe Alabastro, @Jared Goddard | #tech-marketing-internal |

---

## Service Map

All services at the repo root:

| Service | Agent | How NR is Updated | Key File |
|---|---|---|---|
| accounts_service | Python APM | Edit `requirements.txt` | `accounts_service/requirements.txt` |
| auth_service | Python APM | Edit `requirements.txt` | `auth_service/requirements.txt` |
| bill_pay | Python APM | Edit `requirements.txt` | `bill_pay/requirements.txt` |
| notifications_service | Python APM | Edit `requirements.txt` | `notifications_service/requirements.txt` |
| scheduler_service | Python APM | Edit `requirements.txt` | `scheduler_service/requirements.txt` |
| transaction_service | Python APM | Edit `requirements.txt` | `transaction_service/requirements.txt` |
| frontend_service | Browser agent | Edit `package.json` + npm install | `frontend_service/package.json` |
| support_service | Python APM (git-pinned) | **SKIP — see note below** | `support_service/requirements.txt` |
| risk_assessment_service | — | No NR agent, skip | — |
| scenario_service | — | No NR agent, skip | — |

### support_service note
`support_service` pins the NR Python agent directly to a git branch:
`newrelic @ git+https://github.com/newrelic/newrelic-python-agent.git@main`
This cannot be updated with a version bump. Skip it in automated runs; update manually only if explicitly directed by the team.

Terraform (nri-bundle):
- `terraform/aks/newrelic/nr_infra_agent.tf` — `helm_release "nri_bundle"`
- `nr-ebpf-agent` is pinned to `1.1.0` in the same file and is **intentionally frozen — do not touch it**.

---

## Workflow

### Step 0: Gather inputs

Ask the user which parts they want to run and collect all target versions up front before making any changes:

- **Part 1 (nri-bundle)?** If yes → target Helm chart version
- **Part 2 APM agents?** If yes → collect:
  - Python `newrelic` version (e.g., `13.5.0`)
  - Node.js `@newrelic/browser-agent` version (e.g., `1.315.0`)

Check current deployed versions first so the user knows the delta:

```bash
# Python APM (check one — all six services should match)
grep "^newrelic" accounts_service/requirements.txt

# Node.js browser agent
grep "@newrelic/browser-agent" frontend_service/package.json

# nri-bundle (note: currently may be unpinned if no version= line appears)
grep -A 10 'helm_release "nri_bundle"' terraform/aks/newrelic/nr_infra_agent.tf | grep "version\s*="

# nr-ebpf-agent (frozen — for reference only)
grep -A 5 'helm_release "nr_ebpf_agent"' terraform/aks/newrelic/nr_infra_agent.tf | grep "version\s*="
```

---

### Step 1: Pre-flight checks

Verify local runtimes:

```bash
python3 --version
node --version
```

Report the versions to the user. Flag any obvious mismatch vs the services' Dockerfiles before proceeding.

---

### Step 2: nri-bundle (Helm chart via Terraform)

**File:** `terraform/aks/newrelic/nr_infra_agent.tf`

1. Read the file and locate the `helm_release "nri_bundle"` resource.
2. If a `version` field exists, update it to the target version.
   If no `version` field exists (chart is currently unpinned), add `version = "<TARGET_VERSION>"` after the `chart = "nri-bundle"` line.
3. Do **not** touch the `helm_release "nr_ebpf_agent"` resource or its `version = "1.1.0"` line.

After editing, confirm the change with the user before moving to Part 2.

Deployment (human action — do not run):
- Trigger the ReliBank deployment workflow targeting the `newrelic` Terraform module
- Sandbox first, then production

---

### Step 3: Python APM agent

Run for each of the six services: `accounts_service`, `auth_service`, `bill_pay`, `notifications_service`, `scheduler_service`, `transaction_service`.

For each service, edit its `requirements.txt`:
- Find the line matching `newrelic>=...` or `newrelic==...`
- Replace it with `newrelic==<TARGET_VERSION>` (pin to exact version for reproducibility)

After editing all six, confirm the changes look consistent:

```bash
grep "^newrelic" accounts_service/requirements.txt auth_service/requirements.txt bill_pay/requirements.txt notifications_service/requirements.txt scheduler_service/requirements.txt transaction_service/requirements.txt
```

Files to commit: `<service>/requirements.txt` for each updated service.

---

### Step 4: Node.js browser agent (frontend_service)

**File:** `frontend_service/package.json`

1. Find the `@newrelic/browser-agent` entry under `dependencies`.
2. Update the version to `"<TARGET_VERSION>"` (exact pin, no `^` prefix).

```bash
cd frontend_service
npm install
```

Files to commit: `frontend_service/package.json`, `frontend_service/package-lock.json`.

---

### Step 5: Pre-deployment summary

Present a change summary to the user covering every service:

| Service | Component | Old Version | New Version | File(s) Changed |
|---|---|---|---|---|
| (fill in per actual changes made) | | | | |

Remind the user about `support_service` (git-pinned, skipped) so they can decide if a manual follow-up is needed.

Then tell the user:

1. **Review** the diff with `git diff`
2. **Commit** when satisfied: `git add accounts_service/ auth_service/ bill_pay/ notifications_service/ scheduler_service/ transaction_service/ frontend_service/ terraform/ && git commit -m "chore: new relic agent upgrades $(date +%Y-%m-%d)"`
3. **Deploy to Sandbox first** — trigger the deployment workflow
4. **Validate** in sandbox before touching production (see Post-Upgrade Validation below)
5. **Deploy to Production** only after sandbox sign-off

---

## Post-Upgrade Validation (checklist for the user)

Run after each environment deployment:

### Pod health
```bash
kubectl get pods -n relibank
# All pods Running, RESTARTS = 0
kubectl get pods -n newrelic -w
# NR pods Running (for nri-bundle upgrades)
```

### Agent version in New Relic UI
- Go to APM & Services → each upgraded service → check "Agent version" in the metadata panel

### Python agent verification (in AKS)
```bash
kubectl exec <pod-name> -n relibank -- pip show newrelic
```

### Observability checks (New Relic UI)
For each upgraded service, confirm all of these are populated and gap-free:
- **APM graphs**: Web transactions, Throughput, Error rate
- **Distributed Tracing**: Traces arriving and complete, end-to-end
- **Logs**: Appearing with current timestamps
- **Browser**: Browser metrics reporting for frontend_service

A small data gap during the rolling update is normal. A gap >5 minutes post-restart means collection is broken.

### Regression check
Wait for the next scheduled GitHub Actions workflow run. A green run confirms no regressions.

---

## Known Issues & Tribal Knowledge

- Python services pin with `>=` in the repo; after upgrade, this skill pins to `==<TARGET_VERSION>` for reproducibility. That is intentional.
- `support_service` uses a git-branch pin (`@ git+...@main`) — it cannot be updated with a version bump and must be handled manually.
- `nri-bundle` is currently unpinned in Terraform (no `version =` line). Adding the pin during an upgrade run is correct and expected.
- `nr-ebpf-agent` is frozen at `1.1.0` — do not change it.
- `frontend_service` uses the Browser agent (`@newrelic/browser-agent`), not the Node.js APM agent. Do not confuse the two.
- `risk_assessment_service` and `scenario_service` have no NR agent — they are correctly excluded.

---
name: package-update
description: Audit and update packages/libraries across all ReliBank microservices, respecting known pinning constraints, then report a summary. Use when the user asks to update dependencies, bump packages, or run a package/library update across services.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
---

# Package Update Skill

Audit and update packages/libraries across all ReliBank microservices, respecting known pinning constraints, then report a summary of everything changed. Do not ask for approval at any step — run the full workflow end to end and present results at the end.

## Escalation Contacts

| Notify / Escalate | Contact |
|---|---|
| @Jared Goddard, @Gabe Alabastro | #tech-marketing-internal |

---

## Services Map

All services at the repo root:

| Service | Language | Manifest(s) | Notes |
|---|---|---|---|
| accounts_service | Python | requirements.txt | |
| auth_service | Python | requirements.txt | |
| bill_pay | Python | requirements.txt | |
| notifications_service | Python | requirements.txt, azure_function/requirements.txt | Two manifests — update both |
| risk_assessment_service | Python | requirements.txt | |
| scenario_service | Python | requirements.txt | |
| scheduler_service | Python | requirements.txt | |
| transaction_service | Python | requirements.txt | |
| frontend_service | Node.js | package.json | |
| support_service | Python | requirements.txt | **SKIP** — contains a git-pinned NR agent entry; managed separately by nr-agent-upgrade |
| tests/ | Python | requirements.txt | **SKIP** — test-only deps, not a service |

---

## Known Pinning Constraints — enforce silently, never skip

### Python
- **`newrelic` package must not be auto-updated.** It is managed by the `nr-agent-upgrade` runbook.
  Pass `-e newrelic` to `pur` for every Python service.
  Exception: `support_service` is skipped entirely (git-pinned agent entry).

### Node.js
- **`@newrelic/browser-agent` must not be auto-updated.** It is managed by the `nr-agent-upgrade` runbook.
  Pass `--reject @newrelic/browser-agent` to npm-check-updates.

---

## Workflow

Run this end to end. Collect all results as you go, and produce the summary at the very end.

### Step 1: Create a branch

```bash
git checkout main && git pull
git checkout -b chore/package-updates-$(date +%Y%m%d)
```

---

### Step 2: Python services

Repeat for each service in this list:
`accounts_service`, `auth_service`, `bill_pay`, `risk_assessment_service`, `scenario_service`, `scheduler_service`, `transaction_service`

For each service directory:

```bash
cd <service>
pur -r requirements.txt -e newrelic
cd ..
```

Then handle `notifications_service` separately — it has two manifests:

```bash
pur -r notifications_service/requirements.txt -e newrelic
pur -r notifications_service/azure_function/requirements.txt -e newrelic
```

If `pur` is not installed:
```bash
pip3 install pur
```

---

### Step 3: Node.js (frontend_service)

```bash
cd frontend_service
npx npm-check-updates --target minor --reject @newrelic/browser-agent -u
npm install
cd ..
```

---

### Step 4: Commit

```bash
git add accounts_service/ auth_service/ bill_pay/ notifications_service/ risk_assessment_service/ scenario_service/ scheduler_service/ transaction_service/ frontend_service/
git commit -m "chore: package and library updates $(date +%Y-%m-%d)"
```

---

### Step 5: Report summary to the user

Present a single summary covering every service. Include:

1. **Per-service change table** — what moved from what version to what version.
2. **Pins verified** — confirm `newrelic` was excluded from all Python updates and `@newrelic/browser-agent` was excluded from the frontend update.
3. **Skipped services** — `support_service` (git-pinned NR agent) and `tests/` (test deps), with reasons.
4. **Skipped updates** — list anything that had a newer version available but was intentionally skipped (RC, beta, major version jump), with the reason.
5. **What's next** — remind the user to deploy to sandbox, validate observability (APM, Traces, Logs, Infra, DB, Browser in New Relic), and open the PR when satisfied.

Do not push. The user decides when to push.

---

## Rollback

If something breaks after deploy:
1. Deploy `main` to sandbox to restabilize
2. Identify the breaking package from sandbox logs / NR observability
3. Pin the offending package to its previous version in the manifest
4. Rebuild locally to confirm
5. Redeploy to sandbox and revalidate

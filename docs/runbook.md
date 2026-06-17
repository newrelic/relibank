# ReliBank Deployment Runbook

Operational guide. If you're deploying, switching traffic, or recovering from a failed deploy, this is the doc. For *why* the deployer is shaped this way, read [primer.md](primer.md).

---

## TL;DR — the four flows

| Goal | Workflows in order |
|---|---|
| Brand-new environment | `ReliBank Infra` (deploy, stage=all) → `Deploy ReliBank` (deploy, blue) → `Deploy ReliBank` (direct_traffic, blue) |
| Rolling release | `Deploy ReliBank` (deploy, inactive color) → optional canary verify → `Deploy ReliBank` (direct_traffic, new color) → `Deploy ReliBank` (destroy, old color) |
| Infra-only refresh | `ReliBank Infra` (deploy, stage=`ai_services` or `notifications`) |
| Full teardown | `Deploy ReliBank` (destroy) for each color → `ReliBank Infra` (destroy) |

---

## Pre-flight checklist (per environment)

Before any workflow can succeed, the GitHub Environment must exist with the following populated.

### Variables

| Name | Purpose |
|---|---|
| `AKS_CLUSTER_NAME` | e.g. `relibank-sandbox`, `relibank-prod` |
| `AKS_RESOURCE_GROUP` | RG holding the cluster |
| `ACR_NAME` / `ACR_SERVER` | Registry for service images |
| `TF_STATE_STORAGE_ACCOUNT` / `TF_STATE_CONTAINER` | Backend for terraform state |
| `AZURE_LOCATION` | e.g. `westus2` |
| `APP_NAME` | NR APM display root, e.g. `ReliBank (Sandbox)` |
| `DNS_ZONE` | DNS zone for ingress hostname |
| `NR_ACCOUNT_ID` / `NR_BROWSER_APP_ID` | NR account + browser app the frontend reports to |
| `SMS_THROTTLE_PERCENTAGE` | Throttle knob for ACS SMS sender (default 5) |

### Secrets

| Name | Notes |
|---|---|
| `AZURE_CREDENTIALS` | SP JSON blob for `azure/login@v2` |
| `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` / `AZURE_SUBSCRIPTION_ID` / `AZURE_TENANT_ID` | Same SP, broken out for `azurerm` provider |
| `NR_LICENSE_KEY` | APM ingest, ends in `FFFFNRAL` |
| `NR_BROWSER_LICENSE_KEY` | Browser ingest, starts with `NRJS-`. **Different key from above.** See troubleshooting if MFE telemetry breaks. |
| `NR_USER_API_KEY` | NerdGraph user key for tests/automation |
| `MSSQL_SA_USER` / `MSSQL_SA_PASSWORD` | MSSQL admin |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Postgres admin |
| `AZURE_ACS_SMS_PHONE_NUMBER` | Sender phone for SMS |

### One-time Azure / TF state setup

- The deployer service principal must have `Cognitive Services Contributor` at **subscription scope**, not RG-scoped. RG-scoped won't reach soft-deleted accounts (recycle bin lives at sub scope). Without this, AOAI Stage 3 destroy/redeploy fails the second time around.
- Terraform state storage account (e.g. `relibankstate`) and container (`tfstate`) must exist. `setup-environment.sh` creates them if missing.

---

## Manual one-time steps (per environment)

These run once when standing up a new environment, then never again.

### 1. `setup-environment.sh`

```bash
cd terraform/aks/scripts
./setup-environment.sh --environment sandbox
```

Creates RG, ACR, deployer SP, TF state storage. Prints the GitHub secrets/variables to copy into the GH Environment.

### 2. Configure GitHub Environment

Settings → Environments → New environment, name matches the workflow `environment` input (e.g. `sandbox`). Paste in the secrets/variables from step 1.

> **No assistant-creation step.** The deployed AI path is LangGraph chat-completions — see [primer.md → AI architecture](primer.md#ai-architecture-langgraph-not-assistants-api). There is no `create_assistants.py`, no `Bootstrap Assistants` workflow, and no `ASSISTANT_*_ID` to wire. If you find references to those in stale docs or git history, treat them as historical.

---

## Deploy flows — exact step-by-step

### First-time deploy (fresh sandbox)

1. **`ReliBank Infra`** workflow_dispatch
   - `action_type=deploy`
   - `environment=sandbox`
   - `stage=all`
   - Wait ~25 min. Captures NGINX LB IP in the job summary.
2. **`Deploy ReliBank`** workflow_dispatch
   - `action_type=deploy`
   - `environment=sandbox`
   - `target_color=blue`
   - `force_rebuild=false`
   - Wait for image build + TF apply + post-deployment-tests (~15-25 min total).
3. **`Deploy ReliBank`** workflow_dispatch
   - `action_type=direct_traffic`
   - `environment=sandbox`
   - `target_color=blue`
   - Sub-second NGINX rule flip. App is now live.

### Rolling release (env on blue, deploying green)

1. **`Deploy ReliBank`** — `action_type=deploy`, `target_color=green`
2. *(optional)* Canary verify the inactive color before flipping:

   ```bash
   curl -H "X-Test-Env: green" https://relibank-{env}.{dns_zone}/api/health
   ```

3. **`Deploy ReliBank`** — `action_type=direct_traffic`, `target_color=green`
4. *(optional)* Re-run `Test Suite` workflow to verify post-flip.
5. **`Deploy ReliBank`** — `action_type=destroy`, `target_color=blue` (cleanup; not strictly required, but reclaims node pool capacity).

### Infra-only refresh

When AOAI models change or the Function App code/config needs an update — no need to touch the app tier.

- **AOAI rebuild**: `ReliBank Infra` — `action_type=deploy`, `stage=ai_services`. Pre-apply purge handles soft-delete recycle bin first. Idempotent.
- **Notifications rebuild**: `ReliBank Infra` — `action_type=deploy`, `stage=notifications`. Reapplies Function App + ACS, then republishes Function code (`func azure functionapp publish ...`). Both colors pick up the new code automatically — same URL, env-scoped resource.

### Force-rebuild without source change

When build args (NR keys, Stripe keys, browser license key) change but source hasn't:

1. **`Deploy ReliBank`** — set `force_rebuild=true`. This busts the source-hash cache and pushes new images to ACR.
2. **Manual rollout** — terraform sees no spec change so pods don't restart on their own:

   ```bash
   az aks get-credentials -g {AKS_RESOURCE_GROUP} -n {AKS_CLUSTER_NAME} --overwrite-existing
   kubectl rollout restart deployment -n relibank-{color}
   ```

   This is a known gap. See [Known gaps](#known-gaps).

### Full teardown

1. **`Deploy ReliBank`** — `action_type=destroy`, `target_color=blue`
2. **`Deploy ReliBank`** — `action_type=destroy`, `target_color=green`
3. **`ReliBank Infra`** — `action_type=destroy`. Pre-destroy-checks confirms both color namespaces are empty before allowing infra destroy.

---

## Verification commands

After any deploy, sanity-check from a shell with kubeconfig pulled:

```bash
# NGINX LB IP
kubectl get svc ingress-nginx-controller -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# All 10 services up in this color
kubectl get deployments -n relibank-{color}

# Support-service has AOAI env vars wired (endpoint + key)
kubectl exec -n relibank-{color} deploy/support-service -- env \
  | grep -E "AZURE_OPENAI"

# Frontend reachable, browser snippet using NRJS- key
# (open DevTools → Network → filter for bam.nr-data.net)
open https://relibank-{env}.{dns_zone}
```

In the New Relic UI:

- **APM** → entity named `{APP_NAME} - Support Service` should be present, traces flowing.
- **Browser** → app matching `NR_BROWSER_APP_ID` should show PageView + MicroFrontEndTiming events.

---

## Troubleshooting

### AOAI Stage 3 fails with 409 Conflict on apply

Soft-deleted Cognitive Services account in 48h recycle bin from a prior destroy.

- Workflow's pre-apply purge step normally handles it. If it fails:
  - Confirm the deployer SP has `Cognitive Services Contributor` at **subscription scope** (not just RG-scoped).
  - Re-run the workflow.
- Manual purge if needed:

  ```bash
  az cognitiveservices account purge \
    --location {AZURE_LOCATION} \
    --resource-group {AKS_RESOURCE_GROUP} \
    --name relibank-{environment}-openai
  ```

### MFE telemetry tests fail (`test_mfe_single`, `test_microfrontend_telemetry`)

Symptom: basic `PageView` events appear in NR but micro-frontend timing assertions fail.

Cause: frontend was built with the APM key (ends in `FFFFNRAL`) instead of the browser key (starts with `NRJS-`). Beacons route to the NR account's default browser app instead of the configured `NR_BROWSER_APP_ID`, so MFE-specific events are dropped.

Fix:

1. Confirm `NR_BROWSER_LICENSE_KEY` is the NRJS- key. Pull it from NR UI → Settings → the relevant Browser app → JS snippet → `licenseKey` field in the snippet.
2. Re-run `Deploy ReliBank` with `force_rebuild=true` to rebuild the frontend image with the corrected build arg.
3. `kubectl rollout restart deployment/frontend-service -n relibank-{color}` (see force_rebuild gap below).

### `force_rebuild=true` succeeded but pods still running old code

Image was pushed to ACR with the new digest, but TF saw no spec change (same `:blue`/`:green` tag, same env vars), so no rolling update.

Fix:

```bash
kubectl rollout restart deployment -n relibank-{color}
```

### NR Query Performance Monitoring panel empty (no exec plans)

`MSSQL_MEMORY_LIMIT_MB` capped too low. With memory pressure, heavy queries queue indefinitely on `RESOURCE_SEMAPHORE` and never get plan handles, so `dm_exec_query_plan` rows never appear and the QPM exec-plan metric never emits.

Fix: bump `MSSQL_MEMORY_LIMIT_MB` from the prod default of 1024 MB to 6144 MB. Also bump k8s resources (`requests: 4Gi/1cpu`, `limits: 8Gi/2cpu`). Demo loadgen for QPM panels: `utils/scripts/mssql/loadgen/db-direct/run-banking-load.sh` (~25s spending-velocity runs against 2M `BankTransactions`).

### `ReliBank Infra` destroy refuses to run

Pre-destroy-checks job sees deployments still in `relibank-blue` or `relibank-green`. Infra destroy is blocked while app tier is up.

Fix: run `Deploy ReliBank` `action_type=destroy` for each color first, then re-run infra destroy.

### Function App URL changed; one color still calls the old URL

The Function App is **env-scoped** — both colors share one URL. After `stage=notifications` republish, both colors automatically pick up the new code (same URL). If the URL itself changed (rare — it'd require renaming the Function App), the secret in each color's namespace still points at the old URL. Re-deploy each color so the secret refreshes.

### Card payment / payment scenario tests intermittently fail on sandbox

Likely Stripe rate-limit or green-color warm-up window (cold caches, JIT-compiled paths still warming). Re-run after a few minutes. Treat as a real failure only if persistent across multiple runs.

### `db_pool_e2e` passes sandbox, fails prod

Known prod-only regression as of 2026-06-15. Investigate prod-specific config drift (resource limits, db connection-pool size) before assuming the deployer is wrong.

### `terraform plan` shows ARM_* auth errors

The `azurerm` provider doesn't fall back to `az login` credentials in CI. Confirm the workflow has `ARM_CLIENT_ID` / `ARM_CLIENT_SECRET` / `ARM_TENANT_ID` / `ARM_SUBSCRIPTION_ID` in the job's `env:` block. They should be sourced from `secrets.AZURE_CLIENT_ID` etc.

### Test-suite passes on main but the same tests fail locally / in PR

Some tests `pytest.mark.skipif` themselves out when an expected secret is missing or mis-named. A skip looks like a pass in the GitHub summary at a glance. If a secret was renamed (e.g. `NEW_RELIC_USER_API_KEY` → `NR_USER_API_KEY`) and the test still references the old name, it'll silently skip on every run.

Fix: open the GitHub Actions step summary; check for `SKIPPED` in the test summary section, not just the pass/fail count.

---

## Known gaps

These are open items the runbook explicitly acknowledges so you don't waste time hunting for "the missing piece" — there isn't one.

- **`force_rebuild` doesn't trigger rollout.** Image pushes to ACR but TF spec doesn't change, so `imagePullPolicy: Always` only kicks in on pod scheduling, not on existing pods. Always follow `force_rebuild=true` with `kubectl rollout restart`.
- **Sandbox cluster may not exist yet.** Per memory dated 2026-05-15, only `relibank-prod` exists. Check `az aks list -g ReliBank` before assuming sandbox is up.
- **Silent test skips on main.** Test-suite reports passes even when individual tests skipped due to missing/renamed secrets. Read the GH step summary, not just the green checkmark.

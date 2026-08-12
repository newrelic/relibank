# ReliBank Deployment Runbook

Operational guide. If you're deploying, switching traffic, or recovering from a failed deploy, this is the doc. For *why* the deployer is shaped this way, read [primer.md](primer.md).

---

## TL;DR — the five flows

| Goal | Workflows in order |
|---|---|
| Brand-new environment | `ReliBank Infra` (deploy, stage=all) → `Deploy ReliBank` (deploy, blue) → `Deploy ReliBank` (direct_traffic, blue) → *(once services are reporting)* `ReliBank NR` (deploy) |
| Rolling release | `Deploy ReliBank` (deploy, inactive color) → optional canary verify → `Deploy ReliBank` (direct_traffic, new color) → `Deploy ReliBank` (destroy, old color). NR entities don't change on rolling release — entity team triggers `ReliBank NR` (deploy) separately when they merge entity changes. |
| Infra-only refresh | `ReliBank Infra` (deploy, stage=`ai_services` or `notifications`) |
| NR entities + cluster agent refresh | `ReliBank NR` (deploy) — env-scoped, runs against the same NR account the app reports to. Installs/updates the cluster-side `nri-bundle` + `nr-ebpf-agent` helm charts and refreshes NR entity definitions in one apply. Also links the env's Azure subscription to the env's NR account and enables Azure Functions cloud-polling scoped to the env's resource group (`nr_azure_integration.tf`), so the notifications Function App reports without any agent installed in the Function App itself. A follow-up `relibank-newrelic-validate` job hard-gates the workflow by NerdGraph-querying each entity and the cluster's K8sClusterSample/K8sPodSample telemetry. Requires at least one color is deployed and services are reporting (entity data sources resolve real APM entities by name). |
| Full teardown | `ReliBank NR` (destroy) → `Deploy ReliBank` (destroy) for each color → `ReliBank Infra` (destroy). The NR-first ordering is load-bearing: the NR module's helm releases live on the cluster, so `ReliBank Infra` destroy (which tears down the cluster) would orphan that state. |

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
| `NR_USER_API_KEY` | NerdGraph user key. Used by tests, scenario flows, AND the `ReliBank NR` workflow's TF module to CRUD NR entities (dashboards, alerts, SLIs, workloads, synthetics). Must start with `NRAK-`. |
| `MSSQL_SA_USER` / `MSSQL_SA_PASSWORD` | MSSQL admin |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Postgres admin |
| `AZURE_ACS_SMS_PHONE_NUMBER` | Sender phone for SMS |

### One-time Azure / TF state setup

- The deployer service principal must have `Cognitive Services Contributor` at **subscription scope**, not RG-scoped. RG-scoped won't reach soft-deleted accounts (recycle bin lives at sub scope). Without this, AOAI Stage 3 destroy/redeploy fails the second time around.
- The deployer SP also needs `Reader` and `Monitoring Reader` at **subscription scope** (plus the `microsoft.insights` resource provider registered on the subscription) — required by New Relic's Azure cloud-polling integration (`terraform/aks/newrelic/nr_azure_integration.tf`) to enumerate resources and read Azure Monitor metrics for the env's Function App. Sub-scoped for the same reason as Cognitive Services Contributor above — NR's polling does subscription-level discovery even though the integration itself filters down to this env's RG. Without this, the NR Terraform still applies cleanly but polling silently 403s and no `AzureFunctionsAppSample` data appears.
- The deployer SP also needs `User Access Administrator` at the env RG scope so it can create role assignments inside its own RG (e.g. binding the AKS kubelet identity to AcrPull on the ACR). `setup-environment.sh` grants this automatically; if you bootstrap the SP by hand, add it explicitly.
- Terraform state storage account (e.g. `relibankstate`) and container (`tfstate`) must exist. `setup-environment.sh` creates them if missing.

### Hard blockers before first deploy

These four NR Browser app values are required to **build** the frontend image — the Dockerfile's `generate_nrjs_file.sh` fails fast if any are missing. Set them up BEFORE running `Deploy ReliBank` the first time:

- `NR_ACCOUNT_ID` (variable)
- `NR_BROWSER_APP_ID` (variable)
- `NR_BROWSER_LICENSE_KEY` (secret, starts with `NRJS-`)
- `NR_TRUST_KEY` (secret)

All four come from a single New Relic Browser app you create in the NR UI. See [secrets_reference.md → How to create the New Relic browser app](secrets_reference.md#how-to-create-the-new-relic-browser-app-one-time-per-env) for the exact NR UI walkthrough.

---

## Manual one-time steps (per environment)

These run once when standing up a new environment, then never again.

### 1. `setup-environment.sh`

```bash
# from the repo root
cd terraform/aks/scripts
./setup-environment.sh --environment sandbox
```

Creates RG, ACR, deployer SP (with `Contributor`, `User Access Administrator` on the env RG, `Cognitive Services Contributor` at sub scope, `Reader` + `Monitoring Reader` at sub scope, `DNS Zone Contributor` on the shared DNS zone, ACR push/pull, storage blob contributor on the shared TF state account), and TF state storage if missing. Prints the GitHub secrets/variables to copy into the GH Environment.

> **If the SP-creation step hangs or fails silently** — most commonly this is your user identity lacking tenant-level perms to create AAD service principals. As a workaround, run just the `az ad sp create-for-rbac` line manually (or have a tenant admin run it for you), then assign the same roles the script grants:
>
> ```bash
> az ad sp create-for-rbac --name "relibank-<env>-deployer" \
>   --role Contributor \
>   --scopes /subscriptions/<sub>/resourceGroups/ReliBank-<env> /subscriptions/<sub>/resourceGroups/ReliBank
>
> az role assignment create --assignee <appId> --role "User Access Administrator" --scope /subscriptions/<sub>/resourceGroups/ReliBank-<env>
> az role assignment create --assignee <appId> --role "Cognitive Services Contributor" --scope /subscriptions/<sub>
> az role assignment create --assignee <appId> --role "Reader" --scope /subscriptions/<sub>
> az role assignment create --assignee <appId> --role "Monitoring Reader" --scope /subscriptions/<sub>
> az role assignment create --assignee <appId> --role "DNS Zone Contributor" --scope /subscriptions/<sub>/resourceGroups/relibank/providers/Microsoft.Network/dnszones/relibankdemo.com
> # plus AcrPush/AcrPull on the ACR and Storage Blob Data Contributor on the state account
> ```
>
> Then paste the `appId` / `password` / tenant / subscription into the GH Environment secrets directly. Skip Step 4 of `setup-environment.sh` on re-runs by passing `--skip-sp`.

### 2. Configure GitHub Environment

Settings → Environments → New environment, name matches the workflow `environment` input (e.g. `sandbox`). Paste in the secrets/variables from step 1.

> **No assistant-creation step.** The deployed AI path is LangGraph chat-completions — see [primer.md → AI architecture](primer.md#ai-architecture-langgraph-not-assistants-api). There is no `create_assistants.py`, no `Bootstrap Assistants` workflow, and no `ASSISTANT_*_ID` to wire. If you find references to those in stale docs or git history, treat them as historical.

### 3. Add the new env value to workflow `environment` choice lists

Each GitHub Actions workflow that takes an `environment` (or `target_environment`) input declares its allowed values inline. GH won't let you trigger a workflow with a value that isn't in the list, so adding a new env (e.g. `qa`) requires editing every workflow that gates on environment:

- [`.github/workflows/build-push-images.yml`](../../.github/workflows/build-push-images.yml) — `workflow_dispatch.inputs.environment.options`
- [`.github/workflows/deploy-relibank.yml`](../../.github/workflows/deploy-relibank.yml) — `workflow_dispatch.inputs.environment.options`
- [`.github/workflows/relibank-infra.yml`](../../.github/workflows/relibank-infra.yml) — `workflow_dispatch.inputs.environment.options`
- [`.github/workflows/test-suite.yml`](../../.github/workflows/test-suite.yml) — `workflow_dispatch.inputs.target_environment.options`

Recommended: open a small patch PR off `main` that adds the new value to every list at once (don't bundle into feature work — keeps the workflow change reviewable in isolation).

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
4. *(Wait ~1-2 min for services to start reporting to NR.)*
5. **`ReliBank NR`** workflow_dispatch
   - `action_type=deploy`
   - `environment=sandbox`
   - Provisions placeholder NR entities (dashboard, alert policy, SLI, workload, synthetics, etc.) under `${APP_NAME} - Placeholder *`. The entity team replaces these with real definitions over time. **Required before this step:** APM entities must exist in NR — that means at least one color is deployed and services are actively reporting, otherwise the data sources in `terraform/aks/newrelic/nr_entities.tf` fail to resolve at plan time.
   - Also links the env's Azure subscription (shared across all envs) to this env's NR account and turns on Azure Functions cloud-polling scoped to `${AKS_RESOURCE_GROUP}` — see `terraform/aks/newrelic/nr_azure_integration.tf`. This uses the existing deployer service principal; no separate Azure AD app registration is created. Azure Functions telemetry (`AzureFunctionsAppSample`) starts flowing on NR's ~5-minute polling cycle, independent of the entity-search checks below — give it 5-10 minutes before checking, not the 120s used for those.
   - After apply, `relibank-newrelic-validate` waits 120s then runs [`tests/workflow_validation/validate_nr_workflow.py`](../../tests/workflow_validation/validate_nr_workflow.py) — NerdGraph entity-search per TF-created entity (dashboard/alert policy/NRQL condition/destination/channel/workflow/workload/synthetics monitors) and NRQL for `K8sClusterSample` + `K8sPodSample` on the `newrelic` namespace. Any check failing fails the workflow. If a telemetry check fails, give the agents another minute and re-run the workflow (a clean re-apply is a no-op against state).

### Rolling release (env on blue, deploying green)

1. **`Deploy ReliBank`** — `action_type=deploy`, `target_color=green`
2. Canary verify the inactive color before flipping:

   ```bash
   curl -H "X-Test-Env: green" https://relibank-{env}.{dns_zone}/api/health
   ```

3. **`Deploy ReliBank`** — `action_type=direct_traffic`, `target_color=green`
4. Re-run `Test Suite` workflow to verify post-flip.
5. **`Deploy ReliBank`** — `action_type=destroy`, `target_color=blue` (cleanup; not strictly required, but reclaims node pool capacity).

### Scenario Runner UI visibility

Whether the browser page at `/scenario-runner/home` is served (200) or hidden (404) is **derived from the environment — not a workflow input**: **`prod` → hidden, every other environment → shown**. The scenario API (`/scenario-runner/api/*`) is reachable either way, so backend consumers and automation keep working regardless.

The rule lives in `terraform/aks/app_module/main.tf` — the `infrastructure-config` ConfigMap sets `SCENARIO_UI_ENABLED = tostring(var.demo_environment != "prod")`, baked into the scenario-runner pod at startup. So it takes effect on a normal `Deploy ReliBank` of the target environment/color; there's nothing to toggle (and no per-run flag to remember).

**Automated verification.** `tests/test_scenario_service.py::test_scenario_ui_flag_controls_webpage` asserts the page matches the expected state: `/scenario-runner/home` returns 200 (with the page marker) when enabled, else 404, and `/scenario-runner/api/scenarios` stays 200 either way. It's **color-directed** — set `TARGET_COLOR` to send `X-Test-Env: <color>` and validate a specific color (empty = active). The expected state is derived the same way as the deploy: `test-suite.yml` computes `SCENARIO_UI_ENABLED` from `target_environment` (`prod → false`, else `true`), so post-deploy runs validate the just-deployed color **before** cutover with no flag to pass.

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

### NR entities refresh

When the entity team merges entity-definition changes under `terraform/aks/newrelic/`, the changes don't apply automatically — trigger them explicitly:

1. **`ReliBank NR`** — `action_type=deploy`, pick the env. Idempotent; safe to re-run anytime.

If a stub data source in `nr_entities.tf` doesn't resolve (e.g. you added a new service reference before that service was deployed), TF apply fails at plan time. Deploy the missing service first, wait 1-2 min, retry.

### Full teardown

1. **`ReliBank NR`** — `action_type=destroy`. Removes the env's NR entities before the APM data sources go stale (which they do once the app tier stops reporting).
2. **`Deploy ReliBank`** — `action_type=destroy`, `target_color=blue`
3. **`Deploy ReliBank`** — `action_type=destroy`, `target_color=green`
4. **`ReliBank Infra`** — `action_type=destroy`. Pre-destroy-checks confirms both color namespaces are empty before allowing infra destroy.

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

### No `AzureFunctionsAppSample` data after `nr_azure_integration.tf` applies

Symptom: `terraform apply` on `terraform/aks/newrelic` succeeds with no errors, but `SELECT count(*) FROM AzureFunctionsAppSample SINCE 30 minutes ago` in the env's NR account returns nothing, even after 10+ minutes.

Cause: the deployer SP is missing `Reader` + `Monitoring Reader` at **subscription scope** (not RG-scoped). New Relic's Azure polling does subscription-level resource discovery even though `nr_azure_integration.tf` filters results down to the env's RG via `resource_groups`. The Terraform resources (`newrelic_cloud_azure_link_account`/`newrelic_cloud_azure_integrations`) apply cleanly regardless — this is an Azure IAM 403, not a Terraform or NR config error, so there's nothing in the apply output to flag it.

Fix:

- Confirm: `az role assignment list --assignee <deployer SP appId> --all` — look for `Reader` and `Monitoring Reader` at `/subscriptions/<sub>` scope (not a resource-group-scoped entry).
- If missing, grant both:

  ```bash
  az role assignment create --assignee <appId> --role "Reader" --scope /subscriptions/<sub>
  az role assignment create --assignee <appId> --role "Monitoring Reader" --scope /subscriptions/<sub>
  ```

- `setup-environment.sh` grants both automatically for brand-new environment bootstraps — this only applies to environments bootstrapped before that grant was added.

### Azure Functions `functionExecutionCount`/`http5xx` stay empty (but memory/status metrics work)

Symptom: the Function App entity shows up fine in NR, `memoryWorkingSetBytes` and status fields populate normally, but execution count and HTTP error metrics never appear — even right after a confirmed real invocation.

Cause: confirmed by querying Azure Monitor's metrics API directly (`az monitor metrics list --resource <function app resource ID> --metric FunctionExecutionCount`) — Azure itself has zero data points for these metrics, not an NR polling delay. Consumption-plan Function Apps need **Application Insights** connected to generate invocation-level telemetry (request counts, execution counts, per-invocation errors); the generic Azure Monitor platform-metrics collector that NR polls doesn't produce these without it. Memory/instance metrics don't need App Insights since they come from the host directly, which is why those work while everything invocation-related stays empty.

Fix: `terraform/aks/notifications/main.tf` now provisions an `azurerm_log_analytics_workspace` + workspace-based `azurerm_application_insights`, wired into the Function App via `APPLICATIONINSIGHTS_CONNECTION_STRING`. Both new resources are ordinary RG-scoped resources — no extra deployer SP role grants needed beyond the `Contributor` it already has (unlike the AOAI and NR-Azure-polling gaps, which both needed subscription-scope roles). Rolls out to each environment the next time its Stage 4 (`notifications`) is applied — check whether an environment has these two resources yet before assuming this gap is closed there.

Note: this gap was unaffected by the `SIMULATE_NOTIFICATIONS` toggle (see below) even before this fix — execution-count metrics stayed empty whether the Function was really calling ACS or simulating a send, since the root cause was the missing Application Insights connection either way, not send success/failure.

### `notify_user_trigger` invocations are simulated, not real ACS sends

Not a bug — see `notifications_service/README.md` "New Relic Monitoring" and `notifications_service/CLAUDE.md`. Azure Communication Services is currently blocked subscription-wide (`SubscriptionBlocked` for email, `Unauthorized` for SMS), so `SIMULATE_NOTIFICATIONS` defaults to `true` for every environment — the Function logs a send and returns success without calling ACS. If you're validating that real delivery works again after an ACS fix, set `simulate_notifications=false` for that environment (via the `SIMULATE_NOTIFICATIONS` GH Environment variable, or directly in `terraform/aks/notifications/variables.tf`'s default) and redeploy Stage 4, then re-test with a real recipient.

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

### MSSQL out of disk: RelibankDB log filled the data volume

**Symptoms:** The `mssql-0` pod is `Running` but its **log** shows `Error: 1105`/`Error: 1101` (can't allocate space) and sometimes `Operating system error 31` on a tempdb file; `df -h /var/opt/mssql` in the pod is ~99% full. The **in-cluster app** starts failing DB writes (payment/ledger inserts hang or error). Note: this is distinct from the CI `pyodbc … Login timeout expired` symptom, which is a *reachability* problem (see [DB-direct tests can't reach the database from CI](#db-direct-tests-cant-reach-the-database-from-ci)), not a disk problem — a full disk shows up as 1105/1101 in the pod log, not as a connection timeout on the runner.

**Root cause:** `RelibankDB` shipped in **FULL** recovery model with no log-backup job, so the transaction log (`RelibankDB_log.ldf`) grows without bound and fills the (historically 2Gi) PVC. Once the volume is full, SQL Server can't allocate pages and every connection times out.

**Diagnose** (per color — repeat for the active one, and green if you may cut back to it):

```bash
ns=relibank-blue            # or relibank-green
SA=$(kubectl get secret database-credentials -n $ns -o jsonpath='{.data.MSSQL_SA_PASSWORD}' | base64 -d)
SQLCMD=/opt/mssql-tools18/bin/sqlcmd

kubectl exec -n $ns mssql-0 -- df -h /var/opt/mssql          # is it ~99% full?
kubectl exec -n $ns mssql-0 -- sh -c 'du -sh /var/opt/mssql/data/*.ldf'   # log file size
kubectl exec -n $ns mssql-0 -- "$SQLCMD" -S localhost -U sa -P "$SA" -C \
  -Q "SELECT recovery_model_desc, log_reuse_wait_desc FROM sys.databases WHERE name='RelibankDB';"
```

**Fix — step by step.** Shrink first (frees space with no restart), then expand the volume:

1. Switch to SIMPLE recovery and shrink the log (relieves the disk immediately):

   ```bash
   kubectl exec -n $ns mssql-0 -- "$SQLCMD" -S localhost -U sa -P "$SA" -C -Q "
     ALTER DATABASE RelibankDB SET RECOVERY SIMPLE;
     USE RelibankDB; CHECKPOINT;
     DBCC SHRINKFILE (RelibankDB_log, 256);"
   kubectl exec -n $ns mssql-0 -- df -h /var/opt/mssql        # should drop well below 100%
   ```

   > If `log_reuse_wait_desc` is `OLDEST_PAGE` the log may refuse to shrink until the pod is restarted (step 3). Re-run this `CHECKPOINT; DBCC SHRINKFILE` after the restart and it will drop to ~256 MB.

2. Expand the PVC to 8Gi (storageclass `disk.csi.azure.com` has `allowVolumeExpansion=true`):

   ```bash
   kubectl patch pvc mssql-mssql-0 -n $ns -p '{"spec":{"resources":{"requests":{"storage":"8Gi"}}}}'
   ```

3. Finalize the resize — Azure disk grows the filesystem only on remount, so restart the pod once. **This is a brief DB outage; on the active color expect ~1 min where the app can't reach the DB.**

   ```bash
   kubectl delete pod mssql-0 -n $ns
   kubectl rollout status statefulset/mssql -n $ns --timeout=180s
   kubectl exec -n $ns mssql-0 -- df -h /var/opt/mssql        # now ~8Gi
   ```

4. Verify:

   ```bash
   kubectl exec -n $ns mssql-0 -- "$SQLCMD" -S localhost -U sa -P "$SA" -C \
     -Q "SELECT recovery_model_desc, state_desc FROM sys.databases WHERE name='RelibankDB';"   # SIMPLE / ONLINE
   ```

**Prevention (already in IaC):** the PVC template is now `8Gi` (`terraform/aks/app_module/main.tf` `volume_claim_template`, mirrored in `k8s/base/databases/mssql-deployment.yaml`) and `init.sql` sets `RECOVERY SIMPLE` right after `CREATE DATABASE`, so new environments get both automatically.

> ⚠️ **Applying the 8Gi template to an *existing* env replaces the StatefulSet.** A `volume_claim_template` change is immutable, so `terraform apply` will destroy/recreate the `mssql` StatefulSet. StatefulSet PVCs are retained on delete (not garbage-collected), so **data survives** and the new STS re-adopts the existing `mssql-mssql-0` PVC — but the pod restarts. For an already-running env you've patched by hand (steps above), the live PVC is already 8Gi, so this is a no-data-loss pod restart; schedule it, or `terraform state rm kubernetes_stateful_set_v1.mssql` and re-import to avoid the churn.

### DB-direct tests can't reach the database from CI

**Symptoms:** `test_card_payment_transactions` and `test_nrdot_mssql_collector` fail on *every* run (sandbox, staging, analysts) with `pyodbc.OperationalError ('HYT00', ... Login timeout expired)`. HTTP-only tests pass. This is **not** DB health or warm-up — the DB is simply unreachable from the runner.

**Root cause:** those tests open a **direct** SQL connection to `secrets.DB_SERVER:1433`. That only works if MSSQL has a public endpoint. Old prod/`events` was deployed from `k8s/base`, where the mssql Service is `type: LoadBalancer` (`mssql-0`, public IP `relibank-mssql.westus2.cloudapp.azure.com`). The newer **Terraform blue/green deployer** (`app_module`) defines mssql as a **headless ClusterIP** (`cluster_ip = "None"`) with no external IP, so a GitHub-hosted runner has no route to it. HTTP tests still pass because they go through the public ingress LB (`{env}.{dns_zone}`), not the DB.

**Fix — the test suite tunnels to the DB privately; MSSQL stays ClusterIP (matches demogorgon; no public exposure).** `test-suite.yml`'s `python-tests` job, when the target env has AKS vars (`vars.AKS_CLUSTER_NAME != ''`), logs into Azure (`azure/login@v2` + `secrets.AZURE_CREDENTIALS`), runs `az aks get-credentials`, detects the **active color** from `main-ingress`, and `kubectl port-forward`s that color's `svc/mssql` to `127.0.0.1:1433`. Tests then connect to `127.0.0.1` (`DB_SERVER: ${{ secrets.DB_SERVER || '127.0.0.1' }}`), authenticating with the `MSSQL_SA_*` secrets each Terraform env already has (`DB_PASSWORD: ${{ secrets.DB_PASSWORD || secrets.MSSQL_SA_PASSWORD }}`, `DB_USERNAME: ${{ secrets.DB_USERNAME || secrets.MSSQL_SA_USER }}`).

**Zero manual setup for Terraform envs** — no `DB_SERVER`/`DB_PASSWORD` variables or secrets to create. It only requires what a deployable env already has: `AKS_CLUSTER_NAME` / `AKS_RESOURCE_GROUP` **variables** and the `AZURE_CREDENTIALS` **secret**. Just re-run **Relibank Test Suite** (`target_environment={env}`) and `test_card_payment_transactions` / `test_nrdot_mssql_collector` connect over the tunnel.

- **Color is auto-detected**, so it never appears in a hostname or variable — the tunnel just targets the active color's namespace. (Assumes tests run against the live color via `BASE_URL`; add a color override input if canary DB testing of the inactive color is ever needed.)
- **Legacy `events`** has no AKS vars, so the tunnel steps skip and it keeps using its own `DB_SERVER`/`DB_PASSWORD` secrets (which win the `||`) against its public `k8s/base` LoadBalancer.
- The pyodbc connection string already sets `TrustServerCertificate=yes`, so connecting to `127.0.0.1` (cert CN won't match) is fine.

### Infra destroy times out with `context deadline exceeded` on `relibank` namespace

Symptom: Stage 2 (`Terraform Destroy (Stage 2 infra)`) hangs for ~5min with `kubernetes_namespace_v1.relibank: Still destroying...`, then fails with `Error: context deadline exceeded`. `kubectl get ns relibank` shows status `Terminating` and `kubectl get stresschaos -n relibank -o jsonpath='{.items[*].metadata.finalizers}'` returns `["chaos-mesh/records"]`.

Cause: chaos-mesh CRs (StressChaos, PodChaos, etc.) carry a `chaos-mesh/records` finalizer that only the chaos-mesh controller can clear. If the `helm_release.chaos_mesh` resource gets destroyed before the CRs do, the controller disappears, the finalizers stick, and namespace deletion hangs forever.

The infra workflow's pre-Stage-2 cleanup step now handles this automatically — it deletes all chaos-mesh CRs while the controller is still running, then force-clears any leftover finalizers. If you somehow hit this anyway:

```bash
# Find stuck CRs
kubectl get $(kubectl api-resources --api-group=chaos-mesh.org -o name | tr '\n' ',') -A 2>/dev/null

# Force-clear finalizers on each one (replace KIND/NAME/NAMESPACE)
kubectl patch <kind> <name> -n <namespace> --type=merge -p '{"metadata":{"finalizers":[]}}'

# Re-run the infra destroy workflow
```

### `ReliBank Infra` destroy refuses to run

Pre-destroy-checks job sees deployments still in `relibank-blue` or `relibank-green`. Infra destroy is blocked while app tier is up.

Fix: run `Deploy ReliBank` `action_type=destroy` for each color first, then re-run infra destroy.

### Post-deployment tests time out hitting `{env}.{dns_zone}` after a fresh infra rebuild

Symptom: TF apply succeeds, all pods are healthy in `relibank-{color}`, but `Post-deployment tests / python-tests` times out on every request with `requests.exceptions.ConnectTimeout` against `{env}.{dns_zone}` (e.g. `sandbox.relibankdemo.com`). Job runs the full ~63min then fails.

Cause: the DNS A record `{env}.{dns_zone} → NGINX LB IP` is owned by [terraform/aks/traffic_management/main.tf](../terraform/aks/traffic_management/main.tf) and is only updated when the `direct_traffic` action runs. After a full infra rebuild, the cluster's NGINX gets a brand-new LB IP, but the DNS record still points at the previous (now destroyed) cluster's LB IP — so the `Deploy → tests → direct_traffic` order in [first-time-deploy](#first-time-deploy-fresh-sandbox) doesn't actually work end-to-end on a fresh cluster: tests need the IP that `direct_traffic` will eventually publish.

This is a **known gap** in the deploy ordering. The recommended order on a freshly-rebuilt environment is:

1. `Deploy ReliBank` — `action_type=deploy`, `target_color=blue` *(image build + TF apply succeed; tests will fail — that's expected)*
2. `Deploy ReliBank` — `action_type=direct_traffic`, `target_color=blue` *(updates DNS A record + creates ingress rules)*
3. *(optional)* re-run `Test Suite` workflow once DNS has propagated to verify post-deploy-tests pass.

You can verify the LB IP / DNS state directly:

```bash
# What the cluster's NGINX is actually exposing
kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# What public DNS is pointing at
dig +short {env}.{dns_zone}

# These should match. If they don't, run direct_traffic.
```

### `Publish Notifications Function code` fails with `Sequence contains no elements`

Symptom: Stage 4 TF apply succeeds, then the next step (`func azure functionapp publish ...`) fails ~3s after the "Performing remote build" line with `Sequence contains no elements` and exit code 1.

Cause: race between `func` and Azure. The Function App was just created moments earlier; site publishing settings haven't fully propagated yet, so `func` enumerates an empty collection internally and bails.

The publish step now retries up to 3× with 30s backoff. If all three retries still fail:

1. Re-run the workflow with `stage=notifications` (skips cluster/infra/AOAI; just retries the function publish).
2. If that also fails, the Function App itself may be misconfigured. Verify `FUNCTIONS_EXTENSION_VERSION=~4`, `SCM_DO_BUILD_DURING_DEPLOYMENT=1`, `ENABLE_ORYX_BUILD=true` are present in `app_settings`.

### Function App URL changed; one color still calls the old URL

The Function App is **env-scoped** — both colors share one URL. After `stage=notifications` republish, both colors automatically pick up the new code (same URL). If the URL itself changed (rare — it'd require renaming the Function App), the secret in each color's namespace still points at the old URL. Re-deploy each color so the secret refreshes.

### Card payment / payment scenario tests intermittently fail on sandbox

Likely Stripe rate-limit or green-color warm-up window (cold caches, JIT-compiled paths still warming). Re-run after a few minutes. **If `test_card_payment_transactions` / `test_nrdot_mssql_collector` fail *every* run with `pyodbc … Login timeout expired`, that is not warm-up — those tests open a direct DB connection the CI runner can't reach on Terraform-deployed (blue/green) environments. See [DB-direct tests can't reach the database from CI](#db-direct-tests-cant-reach-the-database-from-ci).** (A separate failure mode — a genuinely full DB volume — shows up as `1105`/`1101` in the `mssql-0` pod log; see [MSSQL out of disk](#mssql-out-of-disk-relibankdb-log-filled-the-data-volume).)

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
- **DNS A record only updates on `direct_traffic`.** After a full infra rebuild (cluster destroyed and recreated), the new NGINX LB has a different public IP than the destroyed one, but `{env}.{dns_zone}` still points at the old IP until `direct_traffic` re-applies `traffic_management/`. Post-deployment tests will time out for the entire ~63min suite if you skip `direct_traffic` after a rebuild. See troubleshooting entry above.
- **Silent test skips on main.** Test-suite reports passes even when individual tests skipped due to missing/renamed secrets. Read the GH step summary, not just the green checkmark.
- **Not all Azure regions have Azure OpenAI quota.** During the `analysts` setup, `westus2` and `eastus2` had no AOAI quota — Stage 3 of `ReliBank Infra` failed on AOAI account creation. `westus3` worked. Before standing up a new env, verify your `AZURE_LOCATION` has OpenAI quota:
  ```bash
  az cognitiveservices account list-skus --location <region> --kind OpenAI -o table
  ```
  If the result is empty for your chosen region, pick a different one or request quota through the Azure portal. `setup-environment.sh` defaults to `westus2`, which is unreliable for new subscriptions — override with `--location westus3` (or your verified region) on the initial run.

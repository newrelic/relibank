# Scaling Demo — GitOps Workflow

Simulates a GitOps CI/CD remediation triggered by observed memory pressure on a ReliBank
service pod. When fired, the workflow reads the current replica count from the live AKS cluster,
doubles it, commits the updated Terraform config back to this branch, and applies the change —
producing a visible audit trail in both git history and New Relic logs.

> **Branch note:** The workflow is guarded to run only from `ftr/forrester-workflow`. Triggers
> from any other branch are silently skipped.

---

## Prerequisites — repository secrets and variables

These must be configured on the repository (or the target GitHub environment) before the
workflow can run. Secrets are write-only encrypted values; variables are plaintext.

### Secrets

| Name | Used for |
|------|----------|
| `AZURE_CREDENTIALS` | `azure/login` action — JSON service principal with Contributor access to the AKS resource group |
| `AZURE_CLIENT_ID` | Terraform ARM provider authentication |
| `AZURE_CLIENT_SECRET` | Terraform ARM provider authentication |
| `AZURE_SUBSCRIPTION_ID` | Terraform ARM provider authentication |
| `AZURE_TENANT_ID` | Terraform ARM provider authentication |
| `NR_ANALYSTS_INGEST_KEY` | New Relic Log API — ingest license key for the analysts account (not a user API key) |

> `GITHUB_TOKEN` is provided automatically by GitHub Actions and requires no setup.

### Variables

| Name | Used for |
|------|----------|
| `AKS_CLUSTER_NAME` | `az aks get-credentials` and Terraform `-var` |
| `AKS_RESOURCE_GROUP` | `az aks get-credentials` and Terraform `-var` |
| `TF_STATE_STORAGE_ACCOUNT` | Terraform AzureRM backend — storage account name holding `.tfstate` files |
| `TF_STATE_CONTAINER` | Terraform AzureRM backend — blob container name within the storage account |
| `NR_ACCOUNT_ID_ALERTS` | Embedded in the New Relic log payload as `accountId` |

> Variables and secrets should be scoped to the `analysts` GitHub environment. Environment-scoped
> values take precedence over repository-level values.

---

## Components

| Path | Purpose |
|------|---------|
| `.github/workflows/scaling-demo.yml` | The workflow — dispatched manually or via GitHub API |
| `.github/scripts/export_to_newrelic.py` | Sends the job result to New Relic Log API |
| `terraform/aks/scaling/` | Minimal Terraform module — scales the target deployment via `kubectl scale` |
| `terraform/aks/scaling/scaling.auto.tfvars` | Auto-managed tfvars committed by each workflow run |

---

## Workflow inputs

| Input | Type | Default | Options |
|-------|------|---------|---------|
| `service` | choice | `accounts-service` | all ten ReliBank services |
| `target_color` | choice | `relibank-blue` | `relibank-blue`, `relibank-green` |
| `mode` | choice | `live` | `live`, `demo` |

Environment is hardcoded to `analysts` and is not a selectable input.

**`mode` behavior:**
- `live` — full execution: Azure login, kubectl, Terraform init/apply, rollout verification
- `demo` — simulates the flow without touching infrastructure; Azure login, kubectl, Terraform, and rollout steps are skipped; replica count is hardcoded to `1 → 2`; the GitOps commit still runs; New Relic log is sent with hardcoded `success` status

---

## What happens

1. **Azure login + kubectl** — authenticates to AKS and configures `kubectl` for the target cluster.
2. **Read current replicas** — `kubectl get deployment/<service> -n <target_color> -o jsonpath='{.spec.replicas}'`. Falls back to `1` if the deployment isn't found.
3. **Calculate 2x** — new replica count = current × 2.
4. **Update tfvars** — writes `service_name`, `replicas`, and `target_color` to `terraform/aks/scaling/scaling.auto.tfvars`.
5. **GitOps commit** — commits and pushes the updated tfvars to `ftr/forrester-workflow`. Commit message: `infra: scale <service> to <N> replicas [<env>/<color>]`.
6. **Terraform init + apply** — initialises the scaling module against its own state key (`relibank/<env>/scaling.tfstate`) and runs `kubectl scale` via `null_resource`.
7. **Verify rollout** — `kubectl rollout status` with a 120s timeout; prints the confirmed replica count.
8. **Log to New Relic** — always runs (success or failure); posts a structured log event to the New Relic Log API.

---

## Triggering via GitHub API

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <GITHUB_TOKEN>" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/<owner>/relibank/actions/workflows/scaling-demo.yml/dispatches \
  -d '{
    "ref": "ftr/forrester-workflow",
    "inputs": {
      "service": "accounts-service",
      "target_color": "relibank-blue",
      "mode": "demo"
    }
  }'
```

**Notes:**
- `ref` must be `ftr/forrester-workflow` — the branch guard will skip any other value.
- All three inputs (`service`, `target_color`, `mode`) are required; the API does not apply workflow defaults when inputs are omitted.
- Use `"mode": "demo"` for API-triggered runs from New Relic; use `"mode": "live"` only when intentionally scaling the real cluster.
- A `204 No Content` response means the dispatch was accepted. No run URL is returned.
- Token requires `repo` scope (classic) or `actions: write` (fine-grained).

**Finding the triggered run:**

```bash
curl -H "Authorization: Bearer <GITHUB_TOKEN>" \
  "https://api.github.com/repos/<owner>/relibank/actions/runs?branch=ftr/forrester-workflow&event=workflow_dispatch&per_page=5"
```

---

## New Relic log output

Logs are sent via `export_to_newrelic.py` using secrets `NR_ANALYSTS_INGEST_KEY` and
`NR_ACCOUNT_ID_ALERTS`. They appear under the `Log` event type with `logType = 'GitHubActionsStatus'`.

### NRQL to query

```sql
SELECT * FROM Log
WHERE logType = 'GitHubActionsStatus'
  AND workflowName = 'Scale ReliBank Service'
SINCE 1 hour ago

-- filter to live runs only
SELECT * FROM Log
WHERE logType = 'GitHubActionsStatus'
  AND workflowName = 'Scale ReliBank Service'
  AND runMode = 'live'
SINCE 1 hour ago
```

### Success payload (sent to Log API)

```json
[
  {
    "message": "scaling-demo: accounts-service scaled 1 → 2 replicas in analysts/relibank-blue — success",
    "attributes": {
      "level": "info",
      "logType": "GitHubActionsStatus",
      "jobStatus": "success",
      "jobName": "scale-service",
      "workflowName": "Scale ReliBank Service",
      "failingStepName": "N/A",
      "environment": "analysts",
      "service": "accounts-service",
      "targetColor": "relibank-blue",
      "runMode": "live",
      "replicasBefore": "1",
      "replicasAfter": "2",
      "runUrl": "https://github.com/<owner>/relibank/actions/runs/<run_id>",
      "accountId": "<NR_ACCOUNT_ID>",
      "repository": "<owner>/relibank",
      "failureReason": "N/A"
    }
  }
]
```

### Failure payload

```json
[
  {
    "message": "scaling-demo: accounts-service scaled 1 → 2 replicas in analysts/relibank-blue — failure",
    "attributes": {
      "level": "error",
      "logType": "GitHubActionsStatus",
      "jobStatus": "failure",
      "jobName": "scale-service",
      "workflowName": "Scale ReliBank Service",
      "failingStepName": "N/A",
      "environment": "analysts",
      "service": "accounts-service",
      "targetColor": "relibank-blue",
      "runMode": "live",
      "replicasBefore": "1",
      "replicasAfter": "2",
      "runUrl": "https://github.com/<owner>/relibank/actions/runs/<run_id>",
      "accountId": "<NR_ACCOUNT_ID>",
      "repository": "<owner>/relibank",
      "failureReason": "Job failed in step: 'N/A'. See: https://github.com/<owner>/relibank/actions/runs/<run_id>"
    }
  }
]
```

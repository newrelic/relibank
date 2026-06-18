# ReliBank Blue-Green Deployer

Zero-downtime deployments for ReliBank on Azure AKS. Modeled after the [demogorgon blue-green deployer](../../demogorgon/applications/microservices-demo/terraform/eks/).

---

## How It Works

Two color environments (`blue` and `green`) run in the same AKS cluster in separate namespaces. Only one color serves production traffic at a time. Switching traffic is a single Terraform apply — no pod restarts, sub-second cutover.

```
Internet → NGINX Ingress → blue-service (NGINX proxy) → relibank-blue namespace
                        ↘ green-service (NGINX proxy) → relibank-green namespace
```

Each color has its own:
- AKS user node pool (`blue` or `green`, with `node-color` label)
- Kubernetes namespace (`relibank-blue` or `relibank-green`)
- Full set of 10 application services (pods pinned to the color node pool via `nodeSelector`)
- NGINX proxy in `default` namespace (`blue-service` / `green-service`)

Databases (PostgreSQL, MSSQL) and Kafka live in the shared `relibank` namespace — both colors connect to the same data stores.

---

## Environment Strategy (Option A — One cluster per environment)

Each environment is fully isolated with its own Azure resources:

```
ReliBank/                        # resource group — prod
  relibank                       # ACR
  relibank-prod                  # AKS cluster

ReliBank-Sandbox/                # resource group — sandbox
  relibanksandbox                # ACR (sandbox images isolated from prod)
  relibank-sandbox               # AKS cluster

ReliBank-Staging/                # resource group — staging
  relibankstaging                # ACR
  relibank-staging               # AKS cluster

ReliBank/                        # resource group — shared infra
  relibankstate                  # Storage account for all Terraform state
    tfstate/
      relibank/sandbox/blue.tfstate
      relibank/sandbox/green.tfstate
      relibank/sandbox/traffic_management.tfstate
      relibank/staging/blue.tfstate
      ...
```

Separating ACRs per environment means sandbox image builds never touch production images, which matters when testing new images before promotion.

---

## Directory Structure

```
terraform/aks/
├── app_module/          # Reusable module — creates node pool + all 10 services for one color
├── relibank-blue/       # Blue root module (calls app_module + creates blue NGINX proxy)
├── relibank-green/      # Green root module (calls app_module + creates green NGINX proxy)
├── traffic_management/  # Switches which color receives traffic via NGINX Ingress
└── scripts/
    └── setup-environment.sh   # One-time prerequisite setup for a new environment
```

---

## Workflow

### Full Deploy → Switch → Cleanup cycle

**Step 1 — Deploy new version to inactive color**

Run the `Deploy ReliBank` GitHub Actions workflow:
- `action_type: deploy`
- `environment: sandbox`
- `target_color: green`

This builds images tagged `green` and pushes them to the environment's ACR, then creates the `green` node pool, `relibank-green` namespace, and all 10 service deployments. Green receives 0% traffic.

**Step 2 — Validate (optional)**

Test green before switching using the `X-Test-Env` header:
```bash
curl https://relibank-sandbox.relibankdemo.com -H "X-Test-Env: green"
```

**Step 3 — Switch traffic**

Run workflow:
- `action_type: direct_traffic`
- `environment: sandbox`
- `target_color: green`

NGINX Ingress now routes all traffic to `green-service`. Blue is idle but still deployed.

**Step 4 — Rollback (if needed)**

Re-run `direct_traffic` with `target_color: blue`. Instant — no pod restarts.

**Step 5 — Cleanup old color**

Run workflow:
- `action_type: destroy`
- `environment: sandbox`
- `target_color: blue`

Destroys the blue node pool and all `relibank-blue` namespace resources.

---

## Setting Up a New Environment

Before the first deployment to a new environment, run the setup script:

```bash
./terraform/aks/scripts/setup-environment.sh --environment sandbox
```

The script creates all Azure prerequisites and prints the GitHub secrets and variables to configure. See [scripts/setup-environment.sh](scripts/setup-environment.sh) for all flags.

### What the script creates

- Resource group: `ReliBank-{Environment}` (e.g. `ReliBank-Sandbox`)
- ACR: `relibank{environment}` (e.g. `relibanksandbox`) in the environment resource group
- Service principal: `relibank-{environment}-deployer` scoped to the environment resource group and the shared `ReliBank` resource group (for Terraform state access)
- Verifies the `relibankstate` storage account and `tfstate` container exist (shared, already created)
- Installs NGINX Ingress Controller on the AKS cluster (if the cluster already exists)

### GitHub Environment setup

Each environment needs its own GitHub Environment at **Settings → Environments → New environment**.

#### Variables

- `AKS_CLUSTER_NAME` — AKS cluster name (e.g. `relibank-sandbox`)
- `AKS_RESOURCE_GROUP` — resource group for the cluster (e.g. `ReliBank-Sandbox`)
- `ACR_NAME` — ACR name (e.g. `relibanksandbox`)
- `ACR_SERVER` — ACR login server (e.g. `relibanksandbox.azurecr.io`)
- `TF_STATE_STORAGE_ACCOUNT` — `relibankstate` (shared across all environments)
- `TF_STATE_CONTAINER` — `tfstate` (shared across all environments)
- `DNS_ZONE` — DNS zone for the environment hostname (e.g. `relibankdemo.com`)
- `NR_ACCOUNT_ID` — New Relic account ID for this environment

#### Secrets

- `AZURE_CREDENTIALS` — service principal JSON (output from `az ad sp create-for-rbac`)
- `AZURE_CLIENT_ID` — service principal client ID
- `AZURE_CLIENT_SECRET` — service principal client secret
- `AZURE_SUBSCRIPTION_ID` — Azure subscription ID
- `AZURE_TENANT_ID` — Azure tenant ID
- `NR_LICENSE_KEY` — New Relic ingest license key for this environment's NR account
- `NR_USER_API_KEY` — New Relic user API key for this environment's NR account
- `MSSQL_SA_USER` — MSSQL SA username
- `MSSQL_SA_PASSWORD` — MSSQL SA password
- `POSTGRES_USER` — PostgreSQL username
- `POSTGRES_PASSWORD` — PostgreSQL password

---

## Terraform State

All environments share one storage account (`relibankstate` in `westus2`) but use separate state file paths:

```
relibankstate/tfstate/relibank/{environment}/blue.tfstate
relibankstate/tfstate/relibank/{environment}/green.tfstate
relibankstate/tfstate/relibank/{environment}/traffic_management.tfstate
```

The `--backend-config` flags in the workflow inject the environment name into the key at runtime, so the same Terraform modules serve all environments without modification.

---

## Traffic Switching Details

The `traffic_management` module creates two NGINX Ingress resources:

- Main ingress — routes all traffic to `{target_color}-service` (the active color's NGINX proxy)
- Canary ingress — routes requests with `X-Test-Env: {inactive_color}` header to the inactive color for pre-switch validation

Traffic switch = `terraform apply` with the new `target_color`. No pods are restarted.

---

## Rollback

Rollback is identical to a traffic switch — run `direct_traffic` with the previous color. Because the old color's node pool and pods are still running, rollback is instant.

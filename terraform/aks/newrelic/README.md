# ReliBank — New Relic entities

This directory is owned by the entity-management team (TMM). It defines every New Relic entity attached to ReliBank — dashboards, alert policies, NRQL conditions, notification destinations/channels, workflows, workloads, service levels (SLIs), synthetics monitors, and entity tags — as Terraform. When the `ReliBank NR` workflow runs, the entities in here are created/updated in New Relic.

You do NOT need to touch the workflow plumbing or anything outside this directory. This README explains:

- [Quick Terraform primer](#quick-terraform-primer) — read this first if you've never used Terraform.
- [File layout](#file-layout) — which file owns which entity type.
- [Updating a placeholder](#updating-a-placeholder) — step-by-step recipe.
- [Making entities env-aware](#making-entities-env-aware) — same TF file applies to sandbox, staging, prod; how values differ per env.
- [Testing new entities](#testing-new-entities) — every entity should have a post-apply validation check.

---

## Quick Terraform primer

Five-minute version. Skip if you've already worked with Terraform.

### Resources

A **resource** block says "I want this thing to exist in New Relic." Terraform calls the New Relic API to create it on `apply`, and remembers it in a state file so the next `apply` knows whether to update or skip. Example from [`nr_alerts.tf`](nr_alerts.tf):

```hcl
resource "newrelic_alert_policy" "placeholder" {
  name                = "${var.app_name} - Placeholder Policy"
  incident_preference = "PER_CONDITION"
  account_id          = var.new_relic_account_id
}
```

- `newrelic_alert_policy` — the **resource type** (provider-defined; you don't invent these — they come from the `newrelic/newrelic` provider docs at https://registry.terraform.io/providers/newrelic/newrelic/latest/docs).
- `"placeholder"` — the **local label**. Used to reference this block from other TF code (`newrelic_alert_policy.placeholder.id`). Has nothing to do with the entity name in NR.
- `name`, `incident_preference`, `account_id` — **arguments**. The provider docs list what each resource type accepts.

The full list of resource types supported by the New Relic provider is at https://registry.terraform.io/providers/newrelic/newrelic/latest/docs/resources. When you want to add a new entity type, look it up there to see the argument shape.

### Variables

A **variable** is a parameter passed into the module from the outside. Variables are declared in [`variables.tf`](variables.tf):

```hcl
variable "app_name" {
  description = "NR APM display root, e.g. `ReliBank (Sandbox)`."
  type        = string
}
```

…and consumed elsewhere with `${var.app_name}`:

```hcl
name = "${var.app_name} - Placeholder Policy"
```

When `${var.app_name}` is `ReliBank (Sandbox)`, the resulting NR entity is named `ReliBank (Sandbox) - Placeholder Policy`. When the same TF code runs against `prod`, `${var.app_name}` is `ReliBank (Prod)` instead and the entity is named accordingly — same TF, different value, different entity per environment.

### How variables flow in this project

Three places, in order:

```
┌─────────────────────────┐
│  GH Environment         │   per-env values live here. Sandbox has its own copy of every var/
│  (Settings → Envs)      │   secret; prod has its own copy with different values.
└────────────┬────────────┘
             │  ${{ vars.APP_NAME }}  /  ${{ secrets.NR_USER_API_KEY }}
             ▼
┌─────────────────────────┐
│  .github/workflows/     │   the workflow reads the GH Environment vars/secrets and passes
│  relibank-newrelic.yml  │   them in via `-var="app_name=..." -var="new_relic_..."`
└────────────┬────────────┘
             │  terraform apply -var="app_name=ReliBank (Sandbox)" ...
             ▼
┌─────────────────────────┐
│  terraform/aks/newrelic │   variables.tf declares which vars this module accepts.
│  variables.tf + *.tf    │   nr_*.tf files consume them via `${var.app_name}`.
└─────────────────────────┘
```

The variables relibank-newrelic.yml already passes are documented in [`variables.tf`](variables.tf). Most importantly:

| Variable | Value (example) | What it does |
|---|---|---|
| `app_name` | `ReliBank (Sandbox)` | Prefix for placeholder entity names. Different per env → different entity names per env. |
| `demo_environment` | `sandbox` / `staging` / `prod` | Used in entity tags, synthetics URLs, etc. |
| `new_relic_account_id` | `1234567` | Which NR account to write entities to. |
| `new_relic_user_api_key` | (secret) | NerdGraph auth. |
| `new_relic_license_key` | (secret) | Used by the cluster-side helm agents. |
| `new_relic_region` | `US` / `EU` | NR region. |
| `aks_cluster_name` | `relibank-sandbox` | AKS cluster name for the helm install + cluster telemetry queries. |
| `aks_resource_group` | `ReliBank` | AKS RG. |

### `${...}` interpolation

`"${...}"` injects a value into a string. Common shapes:

- `"${var.app_name} - Latency"` → the value of a variable.
- `"${data.newrelic_entity.support_service.guid}"` → a field from a data source (a "look this up" query).
- `"${newrelic_alert_policy.placeholder.id}"` → a field from another resource. Terraform infers an ordering dependency from this — `placeholder` is created first.

You can also use a value directly without quotes when it's the whole expression:

```hcl
policy_id = newrelic_alert_policy.placeholder.id
```

Both forms work. Use bare references when the value isn't being embedded in a larger string; use `"${...}"` when it is.

---

## File layout

One file per entity type. Find the file that matches what you're adding, drop a new resource block in.

| File | Owns | NR resource types used |
|---|---|---|
| [`nr_alerts.tf`](nr_alerts.tf) | Policies, NRQL conditions, destinations, channels, workflows | `newrelic_alert_policy`, `newrelic_nrql_alert_condition`, `newrelic_notification_destination`, `newrelic_notification_channel`, `newrelic_workflow` |
| [`nr_dashboards.tf`](nr_dashboards.tf) | Dashboards (JSON-backed) | `newrelic_one_dashboard_json` — JSON body lives in [`dashboards/*.json.tftpl`](dashboards/) |
| [`nr_synthetics.tf`](nr_synthetics.tf) | Ping + script monitors | `newrelic_synthetics_monitor`, `newrelic_synthetics_script_monitor` — script body lives in [`scripts/*.tftpl`](scripts/) |
| [`nr_workloads.tf`](nr_workloads.tf) | Workloads | `newrelic_workload` |
| [`nr_service_levels.tf`](nr_service_levels.tf) | Service levels (SLIs) | `newrelic_service_level` |
| [`nr_entity_tags.tf`](nr_entity_tags.tf) | Tag assignments on existing entities | `newrelic_entity_tags` |
| [`nr_entities.tf`](nr_entities.tf) | Data-source lookups for APM/Browser entities (not entities created here) | `data "newrelic_entity"` blocks |

Files you should NOT edit (deployer plumbing):

- [`main.tf`](main.tf) — provider configuration.
- [`variables.tf`](variables.tf) — variable declarations. You DO edit this when [adding a new per-env variable](#adding-a-new-per-env-variable).
- [`backend.tf`](backend.tf), [`outputs.tf`](outputs.tf) — state backend + module outputs.
- [`nr_infra_agent.tf`](nr_infra_agent.tf) — installs the cluster-side NR observability agents (helm). Owned by the deployer team.

---

## Updating a placeholder

Recipe, using a new dashboard as the worked example. The same shape applies to every entity type — copy the existing placeholder block, rename, edit.

### 1. Drop a JSON template in `dashboards/`

Save your dashboard JSON as [`dashboards/<name>.json.tftpl`](dashboards/) — e.g. `dashboards/transaction_overview.json.tftpl`. Keep the `${app_name}` / `${account_id}` template variables consistent with the existing placeholder so the dashboard's `name` field renders correctly. To export an existing dashboard from the NR UI:

1. NR UI → Dashboards → open the dashboard.
2. `...` menu → Copy JSON to clipboard.
3. Paste into `dashboards/<name>.json.tftpl`.
4. Replace the hardcoded `accountId` with `${account_id}` and the title prefix with `${app_name}` (so the same JSON template can render per-env names).

### 2. Wire it up in [`nr_dashboards.tf`](nr_dashboards.tf)

Add a new resource block underneath the existing `placeholder` one. Copy the same shape — only `resource` label, the path to the JSON, and the template-var set change:

```hcl
resource "newrelic_one_dashboard_json" "transaction_overview" {
  json = templatefile("${path.module}/dashboards/transaction_overview.json.tftpl", {
    app_name             = var.app_name
    account_id           = tonumber(var.new_relic_account_id)
    support_service_guid = data.newrelic_entity.support_service.guid
  })
}
```

`templatefile(path, vars)` is a Terraform built-in — it reads the file at `path`, substitutes the `${...}` placeholders inside using `vars`, and returns the rendered string. Add or remove keys from the `vars` map as needed.

### 3. Add a test (see [Testing new entities](#testing-new-entities) below).

### 4. Open a PR, get it merged, trigger the workflow.

TMM does not run `terraform apply` manually. After merge, trigger the `ReliBank NR` workflow with `action_type=deploy environment=<env>` — the workflow applies the change and runs validation. Repeat per environment.

### Other entity types

Same shape: copy the existing placeholder block in the relevant `nr_*.tf` file, rename the resource label, edit the arguments. The argument shapes come from the provider docs at https://registry.terraform.io/providers/newrelic/newrelic/latest/docs/resources/<resource_name>.

Two patterns worth knowing:

- **Resources that reference other resources** (e.g. an NRQL alert condition needs the policy ID) use `<resource_type>.<label>.<field>`:

  ```hcl
  policy_id = newrelic_alert_policy.placeholder.id
  ```

  Terraform figures out the ordering from this — the policy will be created before the condition.

- **Resources that reference NR entities created outside this module** (e.g. an APM service) use the `data` blocks in [`nr_entities.tf`](nr_entities.tf). Add a new `data "newrelic_entity" "<name>"` block per service you need to reference, then use `data.newrelic_entity.<name>.guid` to get its GUID. Note: data sources resolve at plan time, which means the APM entity must already exist in NR — the app tier must be deployed and reporting before this module's apply will succeed.

---

## Making entities env-aware

The same `.tf` files in this directory apply to **sandbox, staging, prod, and analysts**. The differences between environments come from variables. There are two situations:

### Using existing per-env variables

The variables listed in the [variables flow table](#how-variables-flow-in-this-project) — `app_name`, `demo_environment`, `new_relic_account_id`, etc. — are already per-env. **You don't need to do anything extra to use them.** Just interpolate:

```hcl
name = "${var.app_name} - My New Dashboard"   # → "ReliBank (Prod) - My New Dashboard" in prod
```

When the workflow runs against `prod`, the value of `var.app_name` is whatever the prod GH Environment has set — different from sandbox, automatically.

### Adding a NEW per-env variable

When you need a value that should differ per environment but isn't already exposed (e.g. a per-env alert threshold, a per-env Slack channel), add a new variable. Three steps:

#### Step 1 — Declare the variable in [`variables.tf`](variables.tf)

```hcl
variable "transaction_error_rate_threshold" {
  description = "Critical-alert threshold for transaction-service error rate (%). Different per env."
  type        = number
}
```

Optional: add `default = 5` if there's a sensible default and you don't want every env to set it explicitly.

#### Step 2 — Pass the value in [`.github/workflows/relibank-newrelic.yml`](../../../.github/workflows/relibank-newrelic.yml)

In **both** the apply and destroy steps, add a new `-var=` line:

```yaml
-var="transaction_error_rate_threshold=${{ vars.TRANSACTION_ERROR_RATE_THRESHOLD }}" \
```

#### Step 3 — Set the per-env value in each GH Environment

GitHub → repo → *Settings → Environments → `sandbox`* → *Variables* → add `TRANSACTION_ERROR_RATE_THRESHOLD = 5`. Repeat for `staging`, `prod`, `analysts` with whatever value each env should use.

#### Step 4 — Consume the variable in the relevant `.tf` file

```hcl
resource "newrelic_nrql_alert_condition" "transaction_error_rate" {
  # ...
  critical {
    operator  = "above"
    threshold = var.transaction_error_rate_threshold
    # ...
  }
}
```

### When to use a variable vs a hardcoded value

Use a variable when the value is **expected to differ per environment** (thresholds, contacts, target URLs) or **expected to change without a code review** (Slack channel, on-call email). Hardcode when the value is the same everywhere and conceptually part of the entity definition (an SLI's NRQL query, an alert's `incident_preference`).

---

## Testing new entities

Every new entity should have a post-apply check in [`../../tests/workflow_validation/validate_nr_workflow.py`](../../../tests/workflow_validation/validate_nr_workflow.py). The `relibank-newrelic-validate` job runs this file after every deploy as a hard gate — if your new entity isn't queryable in NR within ~120 seconds of `terraform apply` finishing, the workflow fails.

### How the validation file is structured

The file has a NerdGraph helper at the top and one `def test_*` function per check. Each test either:

1. Queries NR for the entity by name.
2. Asserts at least one match.

Failure → the test fails → the validation job fails → the workflow fails.

### Pick the right query shape for your entity type

| Entity type | Query shape (helper used) | Example test function |
|---|---|---|
| Dashboard | `entitySearch` with `type = 'DASHBOARD'` | `test_dashboard_entity_exists` |
| Workload | `entitySearch` with `type = 'WORKLOAD'` | `test_workload_entity_exists` |
| Synthetic monitor (ping or script) | `entitySearch` with `type = 'MONITOR'` | `test_synthetics_ping_monitor_exists` |
| Alert policy | `alerts.policiesSearch` | `test_alert_policy_exists` |
| NRQL alert condition | `alerts.nrqlConditionsSearch` | `test_nrql_alert_condition_exists` |
| Notification destination | `aiNotifications.destinations` | `test_notification_destination_exists` |
| Notification channel | `aiNotifications.channels` | `test_notification_channel_exists` |
| Workflow | `aiWorkflows.workflows` | `test_workflow_exists` |
| Service level (SLI) | (not currently exercised — see [Out of scope](#out-of-scope)) | — |

For data-presence checks (e.g. "this dashboard's main query returns rows"), use NRQL via the `run_nrql(nrql)` helper.

### Recipe: add a test for your new entity

1. Open [`validate_nr_workflow.py`](../../../tests/workflow_validation/validate_nr_workflow.py).
2. Find the existing `def test_*` for an entity of the same type — copy the whole function.
3. Rename it (`test_transaction_overview_dashboard_exists`) and update the entity name in the assertion (`"${APP_NAME} - Transaction Overview"`). Keep the query shape — the helper functions handle the GraphQL.
4. Commit alongside the `.tf` change in the same PR.

Worked example — adding the test for the `transaction_overview` dashboard from earlier:

```python
def test_transaction_overview_dashboard_exists():
    """`newrelic_one_dashboard_json.transaction_overview` — Dashboard, queried via entitySearch."""
    assert_entity_exists(f"{APP_NAME} - Transaction Overview", "DASHBOARD")
```

That's it. Two lines.

### Verifying locally

You can't easily run this script locally without API keys and a live NR account. The workflow run is the test loop — push, trigger, watch. If the validate job fails, the pytest output in the job log shows exactly which check failed and what name it looked for.

### Out of scope

- **Service levels (SLIs)** are not currently validated by `validate_nr_workflow.py` — they need a different query shape (SLI list on the parent workload). Add when needed; the placeholder SLI in [`nr_service_levels.tf`](nr_service_levels.tf) is the only one today.
- **Data-presence checks** (e.g. "the dashboard returns data for the chart") are heavier — they need real traffic against the cluster. Use the existing app-tier test suite (`test-suite.yml`) for those rather than this validation script.

---

## See also

- [`../../../docs/deployer/deployer_primer.md`](../../../docs/deployer/deployer_primer.md) — full deployer architecture, including the three-layer model and why NR is its own workflow.
- [`../../../docs/deployer/runbook.md`](../../../docs/deployer/runbook.md) — operational runbook: trigger order, common workflows.
- [`../../../docs/deployer/secrets_reference.md`](../../../docs/deployer/secrets_reference.md) — every GH Environment variable and secret consumed by the deployer.
- demogorgon's `applications/microservices-demo/terraform/newrelic/newrelic/` module — the internal reference layout this directory mirrors. Use it as a richer example of real (non-placeholder) entity definitions.
- New Relic Terraform provider docs — https://registry.terraform.io/providers/newrelic/newrelic/latest/docs.

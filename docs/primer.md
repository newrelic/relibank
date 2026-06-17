# ReliBank Deployer Primer

Conceptual overview of how the deployer is shaped and why. If you want exact step-by-step instructions, read [runbook.md](runbook.md). This doc is for "I'm new here, give me the mental model" or "I'm about to change the deployer and need to know what's load-bearing."

---

## Orientation

ReliBank is a multi-environment, blue/green AKS deployment modeled after the demogorgon pattern.

- Each **environment** (`sandbox`, `staging`, `prod`) is its own AKS cluster + ACR + set of TF state files.
- Within an environment, two **colors** (`blue`, `green`) run side-by-side in their own namespaces and node pools.
- An NGINX Ingress Controller in front of both colors flips traffic between them on a single TF apply.

That's the whole macro story. Everything below is "how does the deployer encode that."

---

## The two workflows and why they're split

| Workflow | Scope | Run cadence | What it owns |
|---|---|---|---|
| [`relibank-infra.yml`](../.github/workflows/relibank-infra.yml) | env-scoped | rarely | Cluster, cluster-wide infra, AOAI, Function App + ACS |
| [`deploy-relibank.yml`](../.github/workflows/deploy-relibank.yml) | color-scoped | often | One app tier (10 services) per color; image build; traffic switch |

State files mirror the split — see [terraform/aks/](../terraform/aks/):

```
relibank/{env}/cluster.tfstate            ← infra workflow, Stage 1
relibank/{env}/infra.tfstate              ← infra workflow, Stage 2
relibank/{env}/ai_services.tfstate        ← infra workflow, Stage 3
relibank/{env}/notifications.tfstate      ← infra workflow, Stage 4
relibank/{env}/blue.tfstate               ← deploy workflow (blue)
relibank/{env}/green.tfstate              ← deploy workflow (green)
relibank/{env}/traffic_management.tfstate ← deploy workflow (direct_traffic)
```

### The split is load-bearing — the blue/green isolation rule

**Env-scoped resources must never be modified in a per-color deploy.**

Anything with one URL per environment that *both colors call* — Function App, AOAI, ACS — lives in the infra workflow. If a per-color deploy republished Function code, a green deploy would instantly regress blue in production. That's not a hypothetical; it's the reason for the split. When in doubt: "is there one URL per env or two URLs (one per color)?" One URL → infra workflow. Two URLs → deploy workflow.

---

## Stages of `relibank-infra.yml`

Run in order on a fresh deploy; controlled by the `stage` input.

| Stage | Directory | Owns |
|---|---|---|
| 1. Cluster | [terraform/aks/cluster](../terraform/aks/cluster/) | AKS cluster + system node pool |
| 2. Cluster-wide infra | [terraform/aks/infra](../terraform/aks/infra/) | NGINX Ingress Controller, `relibank` namespace for shared DBs / Kafka |
| 3. AI services | [terraform/aks/ai_services](../terraform/aks/ai_services/) | AOAI account + model deployments. Pre-apply purge step defends against the soft-delete recycle bin (48h retention). No Assistants-API entities are created — see [AI architecture](#ai-architecture-langgraph-not-assistants-api) below. |
| 4. Notifications | [terraform/aks/notifications](../terraform/aks/notifications/) | Function App + ACS + email service. Function code is **published in this stage**, not in per-color deploy. |

**Decision point — the `stage` input.** Default `all` runs Stages 1–4 in order. Pick `ai_services` to rebuild AOAI when models change; pick `notifications` to refresh Function code/ACS. Both of those single-stage paths are idempotent.

**Destroy ordering** is the reverse — Stage 4 first (notifications), then 3, 2, 1 — so dependencies tear down cleanly.

---

## Stages of `deploy-relibank.yml`

| Job | What it does |
|---|---|
| `trigger-image-build` | Calls [`build-push-images.yml`](../.github/workflows/build-push-images.yml) — builds 15 service images, tags with color + env, pushes to ACR. Honors source-hash cache; `force_rebuild=true` busts it. |
| `deploy-relibank` | TF apply on [`terraform/aks/relibank-{color}`](../terraform/aks/), which calls the [`app_module`](../terraform/aks/app_module/) to provision color node pool, namespace, and 10 service deployments. AOAI endpoint/key + Function URL pulled from infra workflow's state via `terraform_remote_state`. |
| `post-deployment-tests` | Calls [`test-suite.yml`](../.github/workflows/test-suite.yml) workflow_call — runs Python + frontend tests against the freshly deployed color. |
| `direct-traffic-relibank` | TF apply on [`terraform/aks/traffic_management`](../terraform/aks/traffic_management/) to flip the NGINX main rule. Sub-second cutover, no pod restart. The canary ingress (X-Test-Env header) lets you smoke-test the inactive color before flipping. |
| `destroy-relibank` | Destroys app tier in one color. Use after traffic has been switched away. |

---

## Decision points cheat sheet

When you trigger a workflow, here's what each input is asking:

| Input | What it's asking |
|---|---|
| `environment` | Which cluster/RG/ACR/state path to target. Gated environments may require approval. |
| `target_color` | Which color to mutate or switch traffic to. Almost always: "the inactive color" for deploys, "the new color" for direct_traffic, "the old color" for destroys. |
| `action_type` | `deploy` mutates state forward. `destroy` reverses (infra destroy needs app tier torn down first). `direct_traffic` only flips ingress rules, no app changes. |
| `stage` (infra only) | Full set or one component. Pick narrow when you know exactly which piece changed. |
| `force_rebuild` | Ignore source-hash cache. Use when build args changed but source didn't (NR keys, Stripe keys, browser license key). **Manual `kubectl rollout restart` follow-up required** — known gap. |
| `assistant_b_delay_seconds` | Demo knob. Injects artificial latency into the Specialist agent. Set to `8` to demonstrate the AI bottleneck story. |

---

## The blue/green contract

| Color-scoped (per blue/green) | Env-scoped (shared) |
|---|---|
| Namespace (`relibank-blue` / `relibank-green`) | Cluster |
| Node pool | NGINX Ingress Controller |
| App deployments (10 services) | AOAI account |
| NGINX color proxy | Function App + ACS |
|  | Postgres, MSSQL, Kafka |

Traffic switch: one TF apply on `traffic_management/`. Rollback: identical, reapply with the previous color. Both colors run continuously between releases — that's the cost of zero-downtime, and it's why you periodically destroy the inactive color to reclaim node-pool capacity.

The inactive color is reachable for smoke tests via the canary ingress:

```bash
curl -H "X-Test-Env: green" https://relibank-{env}.{dns_zone}/api/health
```

---

## Key invariants

These three rules came from real incidents. They're not arbitrary; ignoring them recreates the original bug.

### 1. Sandbox-mimics-prod

Sandbox-on-deployer must behave identically to prod (which started life hand-built). Any divergence is a deployer bug, not a test or sandbox quirk.

The trap to watch for: tests on `main` may `pytest.mark.skipif` themselves out when a renamed secret breaks their check (e.g. `NEW_RELIC_USER_API_KEY` → `NR_USER_API_KEY`). Skips look like passes in the GH summary. When sandbox-on-deployer "fails" but prod "passes," verify prod isn't silently skipping the test before assuming the deployer is wrong.

### 2. Two New Relic license keys

The frontend needs *two* distinct New Relic ingest keys, and the deployer plumbs them through different paths.

| Key | Format | Purpose | Where it goes |
|---|---|---|---|
| APM ingest (`NR_LICENSE_KEY`) | `<32 hex chars>FFFFNRAL` | Server-side agent telemetry | App container env, all 10 services |
| Browser ingest (`NR_BROWSER_LICENSE_KEY`) | `NRJS-<20 hex chars>` | Frontend beacon ingest | Built into `nr.js` snippet at frontend image build time |

Wiring the APM key into the browser snippet silently routes beacons to the NR account's default browser app instead of the configured `NR_BROWSER_APP_ID`. Basic `PageView` events still appear, but `MicroFrontEndTiming` events never emit. The browser key comes from NR UI → Settings → the relevant Browser app → JS snippet → `licenseKey` field.

### 3. AOAI soft-delete is real

Cognitive Services accounts retain in a 48h recycle bin after destroy. If a destroy was interrupted or state diverged, the next apply gets a 409 Conflict on create because the name is reserved. Two pieces make destroy/redeploy cycles safe:

1. **Pre-apply purge step** in `relibank-infra.yml` Stage 3 — clears any orphan in the recycle bin before applying. Idempotent.
2. **Subscription-scoped role** on the deployer SP — `Cognitive Services Contributor` must be at sub scope, not RG scope, because the recycle bin lives at sub scope.

If destroy/redeploy starts failing, check both pieces are still in place.

### 4. AI architecture: LangGraph, not Assistants API

The deployed AI flow in `support-service` is a **LangGraph chat-completions** workflow. Coordinator and Specialist are graph nodes built with `AzureChatOpenAI` / `create_agent` — they hit the standard chat-completions endpoint and orchestrate via in-process state. **The OpenAI Assistants API is not used in production.**

What this means concretely:

- **No `assistants.create()` happens at deploy time.** No `asst_...` IDs need to be created, stored, or wired into pods.
- **The only AOAI runtime config support-service needs** is `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` (runtime-injected by `app_module`) plus `ASSISTANT_B_DELAY_SECONDS` (the demo bottleneck knob) and the deployed model name.
- **Vestigial state to ignore.** Some prod cluster pods may have `ASSISTANT_A_ID` / `ASSISTANT_B_ID` set in their env from a frozen pre-LangGraph image. Those values are dead — nothing reads them. Don't reintroduce wiring for them.

**Why this section exists** — the codebase originally used the Assistants API and a `create_assistants.py` bootstrap script. That path was migrated to LangGraph but left scaffolding behind: dead env-var reads, an orphan `support_service_assistants.py` class, a `setup_k8s_azure.sh` cluster-config script, and stale support_service `*.md` docs. All of it has since been removed. This section is the breadcrumb that prevents the next reader from looking at `os.getenv("ASSISTANT_A_ID")` (or grep history for "assistants") and concluding the AI flow needs assistant entities. It doesn't.

If you genuinely want to add an Assistants-API path back, do it deliberately — don't lean on leftover env vars or scripts as evidence that "it's already wired." See the architecture note at the top of [support_service.py](../support_service/support_service.py) for the same warning at the code level.

---

## Map to past incidents

The invariants above are not hypothetical; each one came from an incident that wasn't visible in the code until something broke. Quick crib sheet for tracing back to root cause:

| Invariant / gotcha | Why it exists |
|---|---|
| Subscription-scoped `Cognitive Services Contributor` | Initial deploy worked; second destroy/apply cycle failed with 403 because the SP couldn't reach the sub-scoped recycle bin. |
| Pre-apply AOAI purge step | State divergence (manual `terraform state rm`, network flake mid-destroy, interrupted CI run) leaves orphans the next apply 409s on. |
| Function App + AOAI in infra workflow only | Early version put Function code publish in per-color deploy. A green deploy republished function code mid-day and regressed blue in prod. |
| Frontend uses NRJS- key, not FFFFNRAL | Initial wiring used the APM key for both. Browser monitoring "worked" (PageViews showed) but MFE timing tests silently failed because beacons routed to the wrong app. |
| `MSSQL_MEMORY_LIMIT_MB=6144`, not 1024 | QPM exec-plan panel was blank in prod for weeks. Heavy queries queued on `RESOURCE_SEMAPHORE` waiting for memory and never got plan handles. |
| `force_rebuild` requires manual rollout | `imagePullPolicy: Always` only kicks in on pod scheduling, not on existing pods. With a static `:blue`/`:green` tag and unchanged TF spec, nothing tells k8s to roll. Workaround: `kubectl rollout restart`. Future fix is annotation-based or digest-pinned tags. |

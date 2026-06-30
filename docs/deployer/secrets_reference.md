# Secrets & Variables Reference

Every GitHub Environment variable and secret the deployer reads, what it's for, where to get it, and what breaks if it's wrong. Configure these per environment at *Settings → Environments → `{env}` → Variables / Secrets*.

For workflow flows, see [runbook.md](runbook.md). For why these are split per env, see [primer.md](primer.md).

> **Authoritative source for the Azure portion:** [terraform/aks/scripts/setup-environment.sh](../terraform/aks/scripts/setup-environment.sh). It prints exact values to paste in after running. The NR portion below is what the script can't auto-derive — you have to grab it from the New Relic UI.

---

## Variables (non-secret)

| Variable | Source | Purpose | Failure mode if wrong |
|---|---|---|---|
| `AKS_CLUSTER_NAME` | setup-environment.sh | AKS cluster name (e.g. `relibank-sandbox`, `relibank-prod`) | `az aks get-credentials` fails; deploy can't reach cluster |
| `AKS_RESOURCE_GROUP` | setup-environment.sh | RG holding the cluster | Same as above |
| `ACR_NAME` | setup-environment.sh | Azure Container Registry name (e.g. `relibanksandbox`) | Image push fails |
| `ACR_SERVER` | setup-environment.sh | ACR login server (`{ACR_NAME}.azurecr.io`) | Image push fails |
| `TF_STATE_STORAGE_ACCOUNT` | setup-environment.sh | Backend storage account for TF state (e.g. `relibankstate`) | `terraform init` fails to fetch state |
| `TF_STATE_CONTAINER` | setup-environment.sh | Container in storage account (typically `tfstate`) | Same as above |
| `AZURE_LOCATION` | manual (e.g. `westus2`) | Region for all resources | TF apply fails or creates in wrong region |
| `DNS_ZONE` | manual (e.g. `relibankdemo.com`) | Public DNS zone for ingress hostname | NGINX ingress hostname mismatch; ingress doesn't route |
| `APP_NAME` | manual (e.g. `ReliBank (Sandbox)`) | NR APM app name root. Service entities are named `{APP_NAME} - {Service}`. Drives env-aware separation in the NR UI. | All services in this env collapse onto the wrong APM entity in NR; you can't tell sandbox from prod |
| `NR_ACCOUNT_ID` | NR UI (top-right account picker) | NR account ID (numeric) — frontend snippet, APM agent, test reporting | Frontend doesn't send beacons / agent doesn't ingest |
| `NR_BROWSER_APP_ID` | NR UI → Browser → app → Settings | `applicationID` from the browser app's JS snippet | Beacons land on wrong browser app, MFE telemetry breaks silently |
| `SMS_THROTTLE_PERCENTAGE` | manual (default `5`) | Percentage of SMS sends actually delivered through ACS (rest are no-op'd to avoid Azure charges) | Real SMS to real numbers if too high; 0 SMS if too low |
| `NR_ACCOUNT_ID_ALERTS` | NR UI | Optional — separate NR account for alerting flows. Used only by `flow-stress-chaos.yml` | Alert demo flows fire on wrong account |
| `NR_REGION` | manual (`US` or `EU`) | Optional — defaults to `US` in the `ReliBank NR` workflow if unset. Override only if the env's NR account lives in the EU region. | `newrelic/newrelic` provider authenticates against the wrong region; entity CRUD silently lands on the wrong NR account or fails. |

---

## Secrets

| Secret | Source | Purpose | Failure mode if wrong |
|---|---|---|---|
| `AZURE_CREDENTIALS` | setup-environment.sh (JSON blob) | Used by `azure/login@v2` action | `az` commands fail in workflow |
| `AZURE_CLIENT_ID` | setup-environment.sh | SP appId — fed to `azurerm` provider as `ARM_CLIENT_ID` | TF auth fails (`azurerm` doesn't fall back to az CLI in CI) |
| `AZURE_CLIENT_SECRET` | setup-environment.sh | SP secret — `ARM_CLIENT_SECRET` | Same as above |
| `AZURE_SUBSCRIPTION_ID` | setup-environment.sh | `ARM_SUBSCRIPTION_ID` | TF apply targets wrong subscription |
| `AZURE_TENANT_ID` | setup-environment.sh | `ARM_TENANT_ID` | TF auth fails |
| `NR_LICENSE_KEY` | NR UI → API keys → Ingest – License | **APM** ingest. Server-side agents send traces/metrics with this. Also injected into the cluster-side `nri-bundle` / `nr-ebpf-agent` helm charts installed by `relibank-newrelic.yml`. Format: `<32 hex chars>FFFFNRAL`. | No APM data in NR for any service; no cluster-side infrastructure/Kubernetes/logging/prometheus telemetry either |
| `NR_BROWSER_LICENSE_KEY` | NR UI → Browser → app → Settings → JS snippet → `licenseKey` | **Browser** ingest. Frontend `nr.js` snippet uses this. Format: `NRJS-<20 hex chars>`. **Different key from `NR_LICENSE_KEY`** — not auto-derivable. | If you wire APM key here: `PageView` events leak to NR account default app, `MicroFrontEndTiming` and `.register()` events silently drop, MFE telemetry tests fail |
| `NR_USER_API_KEY` | NR UI → API keys → User | NerdGraph queries from tests + scenario flows. **Also drives the `ReliBank NR` workflow's TF module** — the `newrelic/newrelic` provider uses this for entity CRUD (dashboards, alerts, SLIs, workloads, synthetics). Must start with `NRAK-`. | Test suite reports skip/false-pass on NR-querying tests; `ReliBank NR` workflow fails at provider init. |
| `NR_TRUST_KEY` | NR UI → Browser → app → JS snippet → `trustKey` | Parent account in NR org hierarchy (for cross-app browser linkage) | Browser app can't link to APM, distributed tracing in browser broken |
| `MSSQL_SA_USER` | manual (typically `SA`) | MSSQL admin username | DB connections fail |
| `MSSQL_SA_PASSWORD` | manual | MSSQL admin password (must meet MSSQL complexity policy) | DB connections fail; container may refuse to start |
| `POSTGRES_USER` | manual (typically `postgres`) | Postgres admin username | accounts-service / auth-service connections fail |
| `POSTGRES_PASSWORD` | manual | Postgres admin password | Same as above |
| `AZURE_ACS_SMS_PHONE_NUMBER` | Azure portal → ACS → Phone numbers | E.164 ACS-purchased number (e.g. `+1XXXXXXXXXX`). Reuse prod's number for non-prod envs to avoid duplicate cost. | SMS sends fail; notifications-service errors |
| `NR_LICENSE_KEY_ALERTS` | NR UI (the alerts account) | APM license key for the separate alerts NR account, used only by `flow-stress-chaos.yml` | Alert demo flows can't ingest |

---

## How to create the New Relic browser app (one-time per env)

`setup-environment.sh` handles Azure resources but **can't create the NR browser app for you** — there's no public NR API for it that's worth the wiring. Do this manually before the first `Deploy ReliBank` run, or your frontend will report telemetry to a fallback browser app and `NR_BROWSER_APP_ID` will be wrong.

### Steps

1. **NR UI → Browser** (left nav).
2. **Add a browser app**.
3. **Select instrumentation method: "Copy/Paste"** (NOT APM-linked). This is critical — the APM-linked option doesn't give you a usable license key for our build pipeline; it relies on agent injection that we don't use.
4. **App name**: match the env, something like `ReliBank Frontend (Sandbox)`. This is what appears in the Browser app list, so make it env-disambiguating.
5. **Settings to enable**:
   - SPA monitoring → ON (frontend is a Vite SPA)
   - Distributed tracing → ON (so APM traces correlate with browser sessions)
6. NR returns a **JavaScript snippet**. From the snippet, extract these four values — they map directly to the GH Environment vars/secrets:

   | From snippet | Goes into |
   |---|---|
   | `loader_config.applicationID` (numeric) | `NR_BROWSER_APP_ID` (variable) |
   | `loader_config.licenseKey` (`NRJS-...`) | `NR_BROWSER_LICENSE_KEY` (secret) |
   | `loader_config.accountID` (numeric) | `NR_ACCOUNT_ID` (variable) — same as APM |
   | `loader_config.trustKey` (numeric) | `NR_TRUST_KEY` (secret) |

   Do **not** copy the entire snippet into a secret. The frontend's [`generate_nrjs_file.sh`](../frontend_service/generate_nrjs_file.sh) reconstructs the snippet at image build time by substituting these four values into [`frontend_service/app/nr.js`](../frontend_service/app/) (template with `__APPLICATION_ID__` / `__LICENSE_KEY__` / `__ACCOUNT_ID__` / `__TRUST_KEY__` placeholders).

### How to know it worked

After `Deploy ReliBank` finishes:

1. Open `https://relibank-{env}.{dns_zone}` in a browser.
2. DevTools → Network → filter for `bam.nr-data.net`. You should see beacon POSTs.
3. NR UI → Browser → your app — `PageView` count should tick up within ~30s.
4. Run `Test Suite` workflow with `test_suite=all`. `test_microfrontend_telemetry.py` and `test_mfe_single.py` should pass — if they fail, you almost certainly wired the APM key (`FFFFNRAL` suffix) instead of the browser key (`NRJS-` prefix).

---

## Note: there is no "bootstrap assistants" step

If you arrived here looking for a step to create AOAI Assistants entities (e.g. you saw `ASSISTANT_A_ID` / `ASSISTANT_B_ID` in stale docs or git history), there isn't one. The deployed AI path uses LangGraph chat-completions, not the OpenAI Assistants API. See [primer.md → AI architecture](primer.md#ai-architecture-langgraph-not-assistants-api) for the full explanation and the trap-prevention rationale.

The only AOAI runtime config support-service needs is:

- `AZURE_OPENAI_ENDPOINT` (from `ai_services` TF state, runtime-injected)
- `AZURE_OPENAI_API_KEY` (same)
- `ASSISTANT_B_DELAY_SECONDS` (demo bottleneck knob, set on the deploy workflow's input)

All three already flow through `app_module` automatically.

---

## Where each is consumed (cross-reference)

If you need to trace where something gets used:

| Consumer | Reads |
|---|---|
| [`build-push-images.yml`](../.github/workflows/build-push-images.yml) | `NR_LICENSE_KEY`, `NR_BROWSER_LICENSE_KEY`, `NR_USER_API_KEY`, `NR_TRUST_KEY`, `NR_ACCOUNT_ID`, `NR_BROWSER_APP_ID`, `APP_NAME`, ACR vars |
| [`relibank-infra.yml`](../.github/workflows/relibank-infra.yml) | All Azure secrets, `AZURE_LOCATION`, `AZURE_ACS_SMS_PHONE_NUMBER`, `SMS_THROTTLE_PERCENTAGE`, `AKS_CLUSTER_NAME`, `AKS_RESOURCE_GROUP`, TF state vars |
| [`deploy-relibank.yml`](../.github/workflows/deploy-relibank.yml) | All Azure secrets, MSSQL/Postgres secrets, `DNS_ZONE`, AKS vars, TF state vars |
| [`relibank-newrelic.yml`](../.github/workflows/relibank-newrelic.yml) | All Azure secrets (state backend only), `NR_ACCOUNT_ID`, `NR_USER_API_KEY`, `NR_LICENSE_KEY`, `NR_REGION`, `APP_NAME`, TF state vars |
| [`test-suite.yml`](../.github/workflows/test-suite.yml) | `NR_USER_API_KEY`, `NR_ACCOUNT_ID` |
| [`generate_nrjs_file.sh`](../frontend_service/generate_nrjs_file.sh) | `NR_BROWSER_APP_ID`, `NR_BROWSER_LICENSE_KEY`, `NR_ACCOUNT_ID`, `NR_TRUST_KEY` (passed via Dockerfile build args) |

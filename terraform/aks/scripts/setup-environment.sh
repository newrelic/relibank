#!/usr/bin/env bash
# setup-environment.sh
# One-time prerequisite setup for a new blue-green deployer environment.
# Creates all Azure resources and prints the GitHub secrets/variables to configure.
#
# Usage:
#   ./terraform/aks/scripts/setup-environment.sh --environment sandbox [options]
#
# Options:
#   --environment    Environment name (sandbox, staging, prod)     [required]
#   --cluster        AKS cluster name       (default: relibank-{environment})
#   --resource-group Resource group         (default: ReliBank-{Environment})
#   --acr-name       ACR name               (default: relibank{environment})
#   --location       Azure region           (default: westus2)
#   --skip-nginx     Skip NGINX Ingress Controller installation
#   --skip-acr       Skip ACR creation
#   --skip-sp        Skip service principal creation

set -euo pipefail

# ---- Defaults ----
ENVIRONMENT="staging"
LOCATION="westus2"
SHARED_RESOURCE_GROUP="ReliBank"
STORAGE_ACCOUNT="relibankstate"
CONTAINER_NAME="tfstate"
SKIP_NGINX=true
SKIP_ACR=true
SKIP_SP=false

# ---- Parse arguments ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)   ENVIRONMENT="$2";    shift 2 ;;
    --cluster)       AKS_CLUSTER="$2";    shift 2 ;;
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --acr-name)      ACR_NAME="$2";       shift 2 ;;
    --location)      LOCATION="$2";       shift 2 ;;
    --skip-nginx)    SKIP_NGINX=true;     shift ;;
    --skip-acr)      SKIP_ACR=true;       shift ;;
    --skip-sp)       SKIP_SP=true;        shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$ENVIRONMENT" ]]; then
  echo "ERROR: --environment is required (e.g. --environment sandbox)"
  exit 1
fi

# Capitalize first letter for resource group name (e.g. sandbox → Sandbox)
ENV_CAPITALIZED="$(tr '[:lower:]' '[:upper:]' <<< "${ENVIRONMENT:0:1}")${ENVIRONMENT:1}"

# Set defaults that depend on ENVIRONMENT
AKS_CLUSTER="${AKS_CLUSTER:-relibank-${ENVIRONMENT}}"
RESOURCE_GROUP="${RESOURCE_GROUP:-ReliBank-${ENV_CAPITALIZED}}"
ACR_NAME="${ACR_NAME:-relibank${ENVIRONMENT}}"
ACR_SERVER="${ACR_NAME}.azurecr.io"
SP_NAME="relibank-${ENVIRONMENT}-deployer"

# ---- Colors for output ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
header()  { echo -e "\n${CYAN}========================================${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}========================================${NC}"; }

header "ReliBank Blue-Green Environment Setup: $ENVIRONMENT"

echo ""
info "Configuration:"
echo "  Environment:        $ENVIRONMENT"
echo "  AKS cluster:        $AKS_CLUSTER"
echo "  Resource group:     $RESOURCE_GROUP"
echo "  ACR:                $ACR_SERVER"
echo "  TF state account:   $STORAGE_ACCOUNT (shared, in $SHARED_RESOURCE_GROUP)"
echo "  TF state container: $CONTAINER_NAME"
echo "  Azure location:     $LOCATION"
echo ""

# ---- Prerequisites check ----
header "Checking prerequisites"

for cmd in az kubectl helm; do
  if command -v "$cmd" &>/dev/null; then
    success "$cmd is installed"
  else
    error "$cmd is not installed. Please install it and re-run."
  fi
done

if ! az account show &>/dev/null; then
  error "Not logged in to Azure. Run: az login"
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
success "Azure login OK (subscription: $SUBSCRIPTION_NAME)"

# ---- Step 1: Resource group ----
header "Step 1: Resource Group"

if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
  success "Resource group '$RESOURCE_GROUP' already exists — skipping"
else
  info "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
  az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none
  success "Resource group created"
fi

# ---- Step 2: ACR ----
if [[ "$SKIP_ACR" == "false" ]]; then
  header "Step 2: Container Registry (ACR)"

  if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    success "ACR '$ACR_NAME' already exists — skipping"
  else
    info "Creating ACR '$ACR_NAME' in '$RESOURCE_GROUP'..."
    az acr create \
      --name "$ACR_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --location "$LOCATION" \
      --sku Basic \
      --output none
    success "ACR created: $ACR_SERVER"
  fi
else
  warn "Skipping ACR creation (--skip-acr)"
fi

# ---- Step 3: Terraform state storage (shared) ----
header "Step 3: Terraform State Storage"

if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$SHARED_RESOURCE_GROUP" &>/dev/null; then
  success "Storage account '$STORAGE_ACCOUNT' already exists — skipping"
else
  info "Creating storage account '$STORAGE_ACCOUNT' in '$SHARED_RESOURCE_GROUP'..."
  az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$SHARED_RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --min-tls-version TLS1_2 \
    --output none
  success "Storage account created"
fi

if az storage container show \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode key &>/dev/null; then
  success "Blob container '$CONTAINER_NAME' already exists — skipping"
else
  info "Creating blob container '$CONTAINER_NAME'..."
  az storage container create \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode key \
    --output none
  success "Blob container created"
fi

# ---- Step 4: Service principal ----
if [[ "$SKIP_SP" == "false" ]]; then
  header "Step 4: Service Principal"

  ACR_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ContainerRegistry/registries/${ACR_NAME}"
  ENV_RG_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"
  SHARED_RG_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${SHARED_RESOURCE_GROUP}"
  STORAGE_SCOPE="${SHARED_RG_SCOPE}/providers/Microsoft.Storage/storageAccounts/${STORAGE_ACCOUNT}"

  # Entra ID is eventually consistent, and `az ad sp create-for-rbac` creates the application
  # then immediately references it to create the service principal. That second call can fail
  # with "does not exist or one of its queried reference-property objects are not present",
  # leaving an orphaned app whose generated secret was never printed. Display names are not
  # unique, so a blind re-run would then create duplicates. Hence: separate steps, reuse any
  # app that already exists, and retry past replication lag.
  info "Resolving app registration '$SP_NAME'..."
  APP_OBJECT_ID=$(az ad app list --filter "displayName eq '${SP_NAME}'" --query '[0].id' -o tsv)

  if [[ -n "$APP_OBJECT_ID" ]]; then
    CLIENT_ID=$(az ad app show --id "$APP_OBJECT_ID" --query appId -o tsv)
    warn "App registration already exists ($CLIENT_ID) — reusing it"
  else
    CLIENT_ID=$(az ad app create --display-name "$SP_NAME" --query appId -o tsv)
    APP_OBJECT_ID=$(az ad app list --filter "appId eq '${CLIENT_ID}'" --query '[0].id' -o tsv)
    success "App registration created: $CLIENT_ID"
  fi

  if az ad sp show --id "$CLIENT_ID" &>/dev/null; then
    success "Service principal already exists"
  else
    info "Creating service principal object (allowing for directory replication)..."
    for _ in {1..12}; do
      az ad sp create --id "$CLIENT_ID" -o none 2>/dev/null && break
      sleep 5
    done
    az ad sp show --id "$CLIENT_ID" &>/dev/null \
      || error "Service principal for $CLIENT_ID not creatable after 60s — re-run the script"
  fi

  SP_OBJECT_ID=$(az ad sp show --id "$CLIENT_ID" --query id -o tsv)
  success "Service principal ready: $SP_OBJECT_ID"

  # An existing app's secret value can never be read back, so always mint a fresh one — the
  # point of this step is to emit a usable credential in Step 7. Default clears old secrets.
  info "Generating client secret..."
  CLIENT_SECRET=$(az ad app credential reset --id "$CLIENT_ID" --years 2 --query password -o tsv)
  success "Client secret generated"

  # Assign by object id with an explicit principal type: this skips the Graph lookup that
  # --assignee performs, which is the other place a freshly created principal trips over
  # replication lag. Existing identical assignments are tolerated so re-runs are safe.
  grant() {
    local role="$1" scope="$2" out
    if out=$(az role assignment create \
               --assignee-object-id "$SP_OBJECT_ID" \
               --assignee-principal-type ServicePrincipal \
               --role "$role" --scope "$scope" --output none 2>&1); then
      success "assigned: $role"
    elif grep -qi "already exist" <<<"$out"; then
      warn "already assigned: $role"
    else
      error "Failed to assign '$role' at $scope: $out"
    fi
  }

  info "Granting Contributor on env RG + shared state RG..."
  grant Contributor "$ENV_RG_SCOPE"
  grant Contributor "$SHARED_RG_SCOPE"

  info "Granting AcrPush + AcrPull on $ACR_NAME..."
  grant AcrPush "$ACR_SCOPE"
  grant AcrPull "$ACR_SCOPE"

  # User Access Administrator at ENV RG scope — required so the deployer can create
  # role assignments inside its own RG (e.g. azurerm_role_assignment.acr_pull in
  # terraform/aks/cluster/main.tf binds the AKS kubelet identity to AcrPull on the ACR).
  # Contributor does NOT include Microsoft.Authorization/roleAssignments/write; only
  # Owner and User Access Administrator do. Without this, Stage 1 cluster apply 403s.
  info "Granting User Access Administrator at env RG scope (for azurerm_role_assignment.acr_pull)..."
  grant "User Access Administrator" "$ENV_RG_SCOPE"

  info "Granting Storage Blob Data Contributor on $STORAGE_ACCOUNT..."
  grant "Storage Blob Data Contributor" "$STORAGE_SCOPE"

  # Cognitive Services Contributor at SUBSCRIPTION scope (not RG scope) — required so the deployer
  # can purge soft-deleted Cognitive Services accounts (azurerm_cognitive_account destroy step).
  # The deletedAccounts recycle bin lives at /subscriptions/<sub>/providers/Microsoft.CognitiveServices/locations/<region>/...
  # which is OUTSIDE any RG, so the existing RG-scoped Contributor grant doesn't cover it.
  # Without this, `terraform destroy` of the ai_services module 403s on the purge step and leaves
  # the AOAI account in a soft-delete state.
  info "Granting Cognitive Services Contributor at subscription scope (for AOAI purge on destroy)..."
  grant "Cognitive Services Contributor" "/subscriptions/${SUBSCRIPTION_ID}"

  # The relibankdemo.com zone lives in ReliBank-Prod, not in the shared ReliBank RG or the env's
  # own RG — every environment writes its A record (traffic_management/main.tf) into that one zone.
  # Scope is the zone resource itself, not its RG, so this grants nothing else in ReliBank-Prod.
  info "Granting DNS Zone Contributor on relibankdemo.com zone..."
  DNS_ZONE_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/ReliBank-Prod/providers/Microsoft.Network/dnszones/relibankdemo.com"
  grant "DNS Zone Contributor" "$DNS_ZONE_SCOPE"

  # Reader + Monitoring Reader at SUBSCRIPTION scope — required so New Relic's Azure cloud
  # polling integration (terraform/aks/newrelic/nr_azure_integration.tf) can enumerate resources
  # and read Azure Monitor metrics for this env's Function App. NR's polling does subscription-
  # level discovery even though nr_azure_integration.tf filters results down to this env's RG,
  # so the grant must be sub-scoped, not RG-scoped — same reasoning as the Cognitive Services
  # Contributor grant above. Without this, the NR link/integration Terraform still applies
  # cleanly, but polling silently 403s and no AzureFunctionsAppSample data ever appears.
  info "Granting Reader + Monitoring Reader at subscription scope (for NR Azure Functions polling)..."
  grant "Reader" "/subscriptions/${SUBSCRIPTION_ID}"
  grant "Monitoring Reader" "/subscriptions/${SUBSCRIPTION_ID}"

  info "Ensuring microsoft.insights resource provider is registered (required for NR Azure polling)..."
  az provider register --namespace microsoft.insights
  success "microsoft.insights provider registration ensured"

else
  warn "Skipping service principal creation (--skip-sp)"
  CLIENT_ID="<run without --skip-sp to generate>"
  CLIENT_SECRET="<run without --skip-sp to generate>"
fi

# ---- Step 5: AKS cluster access ----
header "Step 5: AKS Cluster Access"

if az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --overwrite-existing 2>/dev/null; then
  success "kubectl configured for $AKS_CLUSTER"
else
  warn "Cluster '$AKS_CLUSTER' not found — create it first, then re-run with --skip-sp --skip-acr"
  SKIP_NGINX=true
fi

# ---- Step 6: NGINX Ingress Controller ----
if [[ "$SKIP_NGINX" == "false" ]]; then
  header "Step 6: NGINX Ingress Controller"

  if ! kubectl cluster-info &>/dev/null; then
    warn "Cannot connect to cluster — skipping NGINX installation"
  else
    info "Adding ingress-nginx Helm repo..."
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
    helm repo update --cleanup-on-fail 2>/dev/null || helm repo update

    if helm status ingress-nginx -n ingress-nginx &>/dev/null; then
      info "ingress-nginx already installed — upgrading..."
      helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --wait --timeout 5m
    else
      info "Installing ingress-nginx..."
      helm install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --wait --timeout 5m
    fi
    success "NGINX Ingress Controller is ready"

    NGINX_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "<pending>")
    info "NGINX external IP: $NGINX_IP"
    if [[ "$NGINX_IP" == "<pending>" ]]; then
      warn "External IP still provisioning — check with:"
      warn "  kubectl get svc ingress-nginx-controller -n ingress-nginx"
    fi
  fi
else
  warn "Skipping NGINX Ingress Controller installation (--skip-nginx)"
fi

# ---- Step 7: GitHub environment configuration ----
header "Step 7: GitHub Environment Configuration"

AZURE_CREDENTIALS_JSON=$(cat <<ENDJSON
{
  "clientId": "${CLIENT_ID}",
  "clientSecret": "${CLIENT_SECRET}",
  "subscriptionId": "${SUBSCRIPTION_ID}",
  "tenantId": "${TENANT_ID}",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
ENDJSON
)

cat <<EOF

Create a GitHub Environment named '${ENVIRONMENT}' at:
  Settings → Environments → New environment → name: ${ENVIRONMENT}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VARIABLES  (Settings → Environments → ${ENVIRONMENT} → Variables)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AKS_CLUSTER_NAME         = ${AKS_CLUSTER}
AKS_RESOURCE_GROUP       = ${RESOURCE_GROUP}
ACR_NAME                 = ${ACR_NAME}
ACR_SERVER               = ${ACR_SERVER}
TF_STATE_STORAGE_ACCOUNT = ${STORAGE_ACCOUNT}
TF_STATE_CONTAINER       = ${CONTAINER_NAME}
DNS_ZONE                 = relibankdemo.com
NR_ACCOUNT_ID            = <New Relic account ID for ${ENVIRONMENT}>
NR_BROWSER_APP_ID        = <Browser application ID — applicationID from the NR app's JS snippet>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECRETS  (Settings → Environments → ${ENVIRONMENT} → Secrets)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AZURE_CLIENT_ID          = ${CLIENT_ID}
AZURE_CLIENT_SECRET      = ${CLIENT_SECRET}
AZURE_SUBSCRIPTION_ID    = ${SUBSCRIPTION_ID}
AZURE_TENANT_ID          = ${TENANT_ID}
AZURE_CREDENTIALS        = (paste JSON below)
NR_LICENSE_KEY           = <APM ingest license key for ${ENVIRONMENT} — *FFFFNRAL suffix>
NR_BROWSER_LICENSE_KEY   = <Browser license key for ${ENVIRONMENT} — *NRJS-* prefix; pulled from the browser app's JS snippet>
NR_USER_API_KEY          = <New Relic user API key for ${ENVIRONMENT}>
NR_TRUST_KEY             = <Trust key (parent account in NR org hierarchy)>
MSSQL_SA_USER            = SA
MSSQL_SA_PASSWORD        = YourStrong@Password!
POSTGRES_USER            = postgres
POSTGRES_PASSWORD        = your_postgres_password_here
AZURE_ACS_SMS_PHONE_NUMBER = +1XXXXXXXXXX  # E.164 ACS-purchased number (reuse prod's number for non-prod envs)

NOTE: NR_LICENSE_KEY and NR_BROWSER_LICENSE_KEY are DIFFERENT keys for the same account.
  - NR_LICENSE_KEY (FFFFNRAL suffix) authorizes APM/agent ingest.
  - NR_BROWSER_LICENSE_KEY (NRJS- prefix) authorizes browser-agent beacons. It's pulled from the browser
    app's JS snippet in the NR UI (Browser → app → Settings → Application settings) — NOT auto-derivable
    from the APM key. Wiring the APM key into the frontend silently breaks .register() / MicroFrontEndTiming
    events because NR fallback-routes mismatched beacons to a default browser app.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AZURE_CREDENTIALS value (paste this entire JSON block)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${AZURE_CREDENTIALS_JSON}

EOF

# ---- Summary ----
header "Setup Complete"

echo ""
success "Resource group:     $RESOURCE_GROUP"
[[ "$SKIP_ACR" == "false" ]] && success "ACR:                $ACR_SERVER"
success "TF state storage:   $STORAGE_ACCOUNT/$CONTAINER_NAME"
[[ "$SKIP_SP" == "false" ]]  && success "Service principal:  $SP_NAME ($CLIENT_ID)"
[[ "$SKIP_NGINX" == "false" ]] && success "NGINX Ingress:      installed"
echo ""
info "Next steps:"
echo "  1. Add an AKS cluster '$AKS_CLUSTER' to resource group '$RESOURCE_GROUP' if it doesn't exist"
echo "  2. Configure GitHub environment '${ENVIRONMENT}' with the secrets and variables above"
echo "  3. Run 'Deploy ReliBank' workflow:"
echo "       action_type: deploy | environment: ${ENVIRONMENT} | target_color: blue"
echo ""

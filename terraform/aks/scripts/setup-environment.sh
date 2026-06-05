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
ENVIRONMENT=""
LOCATION="westus2"
SHARED_RESOURCE_GROUP="ReliBank"
STORAGE_ACCOUNT="relibankstate"
CONTAINER_NAME="tfstate"
SKIP_NGINX=false
SKIP_ACR=false
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
    --auth-mode login &>/dev/null; then
  success "Blob container '$CONTAINER_NAME' already exists — skipping"
else
  info "Creating blob container '$CONTAINER_NAME'..."
  az storage container create \
    --name "$CONTAINER_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode login \
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

  info "Creating service principal '$SP_NAME'..."
  SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role Contributor \
    --scopes "$ENV_RG_SCOPE" "$SHARED_RG_SCOPE" \
    -o json 2>&1)

  CLIENT_ID=$(echo "$SP_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['appId'])")
  CLIENT_SECRET=$(echo "$SP_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])")

  success "Service principal created: $CLIENT_ID"

  info "Granting AcrPush + AcrPull on $ACR_NAME..."
  az role assignment create --assignee "$CLIENT_ID" --role AcrPush --scope "$ACR_SCOPE" --output none
  az role assignment create --assignee "$CLIENT_ID" --role AcrPull --scope "$ACR_SCOPE" --output none
  success "ACR roles assigned"

  info "Granting Storage Blob Data Contributor on $STORAGE_ACCOUNT..."
  az role assignment create --assignee "$CLIENT_ID" --role "Storage Blob Data Contributor" --scope "$STORAGE_SCOPE" --output none
  success "Storage role assigned"

  info "Granting DNS Zone Contributor on relibankdemo.com zone..."
  DNS_ZONE_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/relibank/providers/Microsoft.Network/dnszones/relibankdemo.com"
  az role assignment create --assignee "$CLIENT_ID" --role "DNS Zone Contributor" --scope "$DNS_ZONE_SCOPE" --output none
  success "DNS Zone Contributor assigned"

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECRETS  (Settings → Environments → ${ENVIRONMENT} → Secrets)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AZURE_CLIENT_ID          = ${CLIENT_ID}
AZURE_CLIENT_SECRET      = ${CLIENT_SECRET}
AZURE_SUBSCRIPTION_ID    = ${SUBSCRIPTION_ID}
AZURE_TENANT_ID          = ${TENANT_ID}
AZURE_CREDENTIALS        = (paste JSON below)
NR_LICENSE_KEY           = <New Relic ingest key for ${ENVIRONMENT}>
NR_USER_API_KEY          = <New Relic user API key for ${ENVIRONMENT}>
MSSQL_SA_USER            = SA
MSSQL_SA_PASSWORD        = YourStrong@Password!
POSTGRES_USER            = postgres
POSTGRES_PASSWORD        = your_postgres_password_here

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

variable "new_relic_account_id" {
  description = "New Relic account ID (numeric). Same value as NR_ACCOUNT_ID in the GH Environment."
  type        = string
}

variable "new_relic_user_api_key" {
  description = "New Relic user API key (NRAK-...). NerdGraph CRUD for entity management."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^NRAK-", var.new_relic_user_api_key))
    error_message = "Expected a New Relic user API key with NRAK- prefix."
  }
}

variable "new_relic_license_key" {
  description = "New Relic license key (FFFFNRAL suffix). Kept here for parity with demogorgon's module signature; not currently consumed by any placeholder resource but useful for future agent/integration wiring."
  type        = string
  sensitive   = true
}

variable "new_relic_region" {
  description = "New Relic region. Valid: US, EU."
  type        = string
  default     = "US"
}

variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod, analysts). Suffixes entity names so per-env entities are disambiguated in the NR UI."
  type        = string
}

variable "app_name" {
  description = "NR APM display root (e.g. `ReliBank (Sandbox)`). Service entities are named `{app_name} - {Service}`; placeholder entities use this as a prefix too."
  type        = string
}

variable "aks_cluster_name" {
  description = "AKS cluster name. Used to data-source kube credentials for the helm/kubernetes providers that install the cluster-side NR observability stack."
  type        = string
}

variable "aks_resource_group" {
  description = "AKS cluster resource group. Pair with aks_cluster_name."
  type        = string
}

variable "azure_client_id" {
  description = "Deployer service principal's application (client) ID. Reused (not a dedicated NR app registration) to authorize New Relic's Azure cloud-polling integration. Same value as ARM_CLIENT_ID / secrets.AZURE_CLIENT_ID."
  type        = string
}

variable "azure_client_secret" {
  description = "Deployer service principal's client secret. Same value as ARM_CLIENT_SECRET / secrets.AZURE_CLIENT_SECRET."
  type        = string
  sensitive   = true
}

variable "azure_tenant_id" {
  description = "Azure AD tenant ID for the deployer service principal. Same value as ARM_TENANT_ID / secrets.AZURE_TENANT_ID."
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure subscription ID (shared across all ReliBank environments). Same value as ARM_SUBSCRIPTION_ID / secrets.AZURE_SUBSCRIPTION_ID."
  type        = string
}

variable "postgres_user" {
  description = "accounts-db Postgres username (same credential the app tier uses). Same value as secrets.POSTGRES_USER."
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "accounts-db Postgres password (same credential the app tier uses). Same value as secrets.POSTGRES_PASSWORD."
  type        = string
  sensitive   = true
}

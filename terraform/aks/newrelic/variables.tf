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

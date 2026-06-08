variable "demo_environment" {
  description = "Environment name (staging, prod, development)"
  type        = string
}

variable "aks_cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "relibank-prod"
}

variable "aks_resource_group" {
  description = "Azure resource group for AKS cluster"
  type        = string
  default     = "ReliBank"
}

variable "acr_server" {
  description = "Azure Container Registry server URL (e.g. relibanksandbox.azurecr.io)"
  type        = string
  default     = "relibank.azurecr.io"
}

variable "new_relic_license_key" {
  description = "New Relic license key"
  type        = string
  sensitive   = true
}

variable "new_relic_account_id" {
  description = "New Relic account ID"
  type        = string
}

variable "mssql_sa_password" {
  description = "MSSQL SA password"
  type        = string
  sensitive   = true
}

variable "mssql_sa_user" {
  description = "MSSQL SA username"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  sensitive   = true
}

variable "tf_state_storage_account" {
  description = "Storage account holding the ai_services remote state"
  type        = string
  default     = "relibankstate"
}

variable "tf_state_container" {
  description = "Blob container holding the ai_services remote state"
  type        = string
  default     = "tfstate"
}

variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod)"
  type        = string
}

variable "aks_cluster_name" {
  description = "AKS cluster name"
  type        = string
}

variable "aks_resource_group" {
  description = "Azure resource group for AKS cluster"
  type        = string
}

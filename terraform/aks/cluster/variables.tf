variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod)"
  type        = string
}

variable "aks_cluster_name" {
  description = "AKS cluster name (e.g. relibank-sandbox)"
  type        = string
}

variable "resource_group_name" {
  description = "Azure resource group to create for this environment (e.g. ReliBank-Sandbox)"
  type        = string
}

variable "acr_name" {
  description = "ACR name — must already exist in this resource group (e.g. relibanksandbox)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westus2"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the AKS cluster"
  type        = string
  default     = "1.32"
}

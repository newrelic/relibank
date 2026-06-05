variable "demo_environment" {
  description = "Environment name (staging, prod, development)"
  type        = string
}

variable "target_color" {
  description = "Active deployment color to send traffic to (blue or green)"
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

variable "dns_zone" {
  description = "DNS zone for the relibank environment hostname"
  type        = string
  default     = "example.com"
}

variable "dns_resource_group" {
  description = "Resource group hosting the Azure DNS zone for var.dns_zone"
  type        = string
  default     = "relibank"
}

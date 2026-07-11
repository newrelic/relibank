variable "service_name" {
  description = "Name of the Kubernetes deployment to scale (e.g. transaction-service)"
  type        = string
}

variable "replicas" {
  description = "Target replica count — set automatically by the scaling-demo workflow"
  type        = number
  validation {
    condition     = var.replicas >= 1 && var.replicas <= 20
    error_message = "replicas must be between 1 and 20."
  }
}

variable "target_color" {
  description = "Deployment color namespace to target (blue or green)"
  type        = string
  default     = "blue"
  validation {
    condition     = contains(["blue", "green"], var.target_color)
    error_message = "target_color must be 'blue' or 'green'."
  }
}

variable "aks_cluster_name" {
  description = "AKS cluster name — used to annotate the scaling operation in outputs"
  type        = string
}

variable "aks_resource_group" {
  description = "Azure resource group containing the AKS cluster"
  type        = string
}

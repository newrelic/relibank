variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for the AOAI account"
  type        = string
}

variable "aks_resource_group" {
  description = "Resource group that hosts the env's AOAI account (same RG as the AKS cluster)"
  type        = string
}

variable "model_deployments" {
  description = <<-EOT
    Model deployments to provision on the AOAI account.

    Default mirrors prod's `relibank-agents` shape: gpt-4-1 (the deployment
    name LangGraphSupportService hardcodes), gpt-4o, and gpt-4o-mini.
    The deployment NAME (map key) is what consumers reference; the underlying
    `model_name` / `model_version` are the actual Azure-side model.
  EOT
  type = map(object({
    model_name    = string
    model_version = string
    capacity      = number
  }))
  default = {
    "gpt-4-1" = {
      model_name    = "gpt-4.1"
      model_version = "2025-04-14"
      capacity      = 5
    }
    "gpt-4o" = {
      model_name    = "gpt-4o"
      model_version = "2024-11-20"
      capacity      = 10
    }
    "gpt-4o-mini" = {
      model_name    = "gpt-4.1-mini"
      model_version = "2025-04-14"
      capacity      = 10
    }
  }
}

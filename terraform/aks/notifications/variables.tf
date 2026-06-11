variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for the Function App + ACS"
  type        = string
}

variable "aks_resource_group" {
  description = "Resource group that hosts the env's notifications resources (same RG as the AKS cluster)"
  type        = string
}

variable "function_plan_sku" {
  description = "App Service Plan SKU. FC1 = FlexConsumption (matches prod). Y1 = Consumption (universally available fallback) if FC1 is unsupported in the region."
  type        = string
  default     = "FC1"
}

variable "sms_sender_phone" {
  description = "ACS phone number used as SMS sender (E.164 format). Required — must be sourced from a GH secret, never hardcoded (public repo)."
  type        = string
  sensitive   = true
}

variable "sms_throttle_percentage" {
  description = "Demo knob — % of SMS recipients that actually receive a message (hash-based sampling in function_app.py). Default 5 mirrors prod; 0 disables SMS for cost-sensitive sandboxes."
  type        = number
  default     = 5
}

# Auto-detects which colors are deployed based on namespace existence.
# Mirrors demogorgon's traffic_management/locals.tf logic exactly.

data "kubernetes_resources" "blue_namespace" {
  api_version    = "v1"
  kind           = "Namespace"
  field_selector = "metadata.name=relibank-blue"
}

data "kubernetes_resources" "green_namespace" {
  api_version    = "v1"
  kind           = "Namespace"
  field_selector = "metadata.name=relibank-green"
}

locals {
  blue_deployed  = length(data.kubernetes_resources.blue_namespace.objects) > 0
  green_deployed = length(data.kubernetes_resources.green_namespace.objects) > 0

  # Inactive color receives the X-Test-Env header routing (pre-switch validation)
  inactive_color = var.target_color == "blue" ? "green" : "blue"
}

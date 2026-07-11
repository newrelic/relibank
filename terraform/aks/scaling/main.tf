# scaling/main.tf
# Scales a target ReliBank service deployment to the specified replica count.
# Triggered by the scaling-demo workflow in response to observed resource pressure.
#
# kubectl is pre-configured by the workflow before terraform apply runs,
# so no Kubernetes provider credentials are needed here.

terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

locals {
  namespace = "relibank-${var.target_color}"
}

resource "null_resource" "scale_deployment" {
  triggers = {
    service_name = var.service_name
    replicas     = var.replicas
    target_color = var.target_color
  }

  provisioner "local-exec" {
    command = "kubectl scale deployment/${var.service_name} --replicas=${var.replicas} -n ${local.namespace}"
  }
}

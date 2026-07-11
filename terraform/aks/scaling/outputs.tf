output "scaled_service" {
  description = "Name of the deployment that was scaled"
  value       = var.service_name
}

output "replica_count" {
  description = "Replica count applied to the deployment"
  value       = var.replicas
}

output "namespace" {
  description = "Kubernetes namespace targeted"
  value       = "relibank-${var.target_color}"
}

output "cluster" {
  description = "AKS cluster where the scaling was applied"
  value       = var.aks_cluster_name
}

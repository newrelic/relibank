output "namespace" {
  description = "Kubernetes namespace for this color deployment"
  value       = kubernetes_namespace_v1.relibank_color.metadata[0].name
}

output "node_pool_id" {
  description = "AKS node pool ID"
  value       = azurerm_kubernetes_cluster_node_pool.relibank_color_np.id
}

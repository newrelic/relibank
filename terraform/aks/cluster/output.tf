output "cluster_name" {
  value = azurerm_kubernetes_cluster.relibank.name
}

output "resource_group_name" {
  value = data.azurerm_resource_group.relibank_env.name
}

output "cluster_id" {
  value = azurerm_kubernetes_cluster.relibank.id
}

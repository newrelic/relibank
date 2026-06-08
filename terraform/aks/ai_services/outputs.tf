output "endpoint" {
  description = "AOAI account endpoint (e.g. https://relibank-sandbox-openai.openai.azure.com/)"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "api_key" {
  description = "AOAI primary access key"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "deployment_names" {
  description = "List of model deployment names available on the account"
  value       = sort(keys(var.model_deployments))
}

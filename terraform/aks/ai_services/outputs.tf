output "endpoint" {
  description = "AOAI account endpoint (e.g. https://relibank-sandbox-openai.openai.azure.com/)"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "api_key" {
  description = "AOAI primary access key"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "assistant_ids" {
  description = "Map of assistant slug → assistant ID (e.g. coordinator → asst_xxx)"
  value       = { for k, v in data.local_file.assistant_id : k => trimspace(v.content) }
}

output "assistant_b_delay_seconds" {
  description = "Demo bottleneck delay (seconds) for Assistant B"
  value       = var.assistant_b_delay_seconds
}

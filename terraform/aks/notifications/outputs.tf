output "function_hostname" {
  description = "Hostname of the deployed Function App (e.g. relibank-sandbox-notifications-fn.azurewebsites.net)"
  value       = azurerm_linux_function_app.notifications.default_hostname
}

output "function_app_name" {
  description = "Name of the Function App resource (used by `func azure functionapp publish` step)"
  value       = azurerm_linux_function_app.notifications.name
}

output "function_url" {
  description = "Full URL of the notify_user_trigger function with default function key embedded as ?code= — consumed by notifications-service via terraform_remote_state."
  value       = "https://${azurerm_linux_function_app.notifications.default_hostname}/api/notify_user_trigger?code=${data.azurerm_function_app_host_keys.notifications.default_function_key}"
  sensitive   = true
}

output "acs_name" {
  description = "ACS resource name (informational — function uses connection string injected via app_settings)"
  value       = azurerm_communication_service.acs.name
}

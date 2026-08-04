# Links this environment's Azure subscription to this environment's New Relic account and
# scopes cloud-polling to Azure Functions telemetry (AzureFunctionsAppSample) for only the
# Function App(s) in this env's resource group.
#
# Reuses the deployer's existing service-principal credentials (see variables.tf) rather than
# provisioning a dedicated NR-only Azure AD app registration — same SP already used for the
# azurerm provider's ARM_* auth in this module and in terraform/aks/notifications. That SP also
# needs Reader + Monitoring Reader at subscription scope for this to actually poll data — see
# terraform/aks/scripts/setup-environment.sh.
#
# Every environment has its OWN New Relic account (var.new_relic_account_id) but all
# environments share ONE Azure subscription — so `resource_groups` below MUST stay scoped to
# this env's RG (var.aks_resource_group), or environments would see each other's Function Apps
# in their polled Azure Functions data.

resource "newrelic_cloud_azure_link_account" "this" {
  account_id      = var.new_relic_account_id
  application_id  = var.azure_client_id
  client_secret   = var.azure_client_secret
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
  name            = "${var.app_name} - Azure"
}

resource "newrelic_cloud_azure_integrations" "this" {
  linked_account_id = newrelic_cloud_azure_link_account.this.id
  account_id        = var.new_relic_account_id

  functions {
    metrics_polling_interval = 300
    resource_groups          = [var.aks_resource_group]
  }
}

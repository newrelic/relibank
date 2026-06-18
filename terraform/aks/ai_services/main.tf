terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

locals {
  account_name = "relibank-${var.demo_environment}-openai"
}

# ---------------------------------------------------------------------------
# Azure OpenAI (Cognitive Services) account.
# `custom_subdomain_name` makes the account reachable at
# https://<subdomain>.openai.azure.com/ for the LangGraphSupportService client.
# ---------------------------------------------------------------------------
resource "azurerm_cognitive_account" "openai" {
  name                  = local.account_name
  resource_group_name   = var.aks_resource_group
  location              = var.location
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = local.account_name

  tags = {
    environment = var.demo_environment
    managed_by  = "terraform"
  }
}

# ---------------------------------------------------------------------------
# Model deployments — one per entry in var.model_deployments. The map key is
# the deployment name (what client code references, e.g. "gpt-4-1").
#
# Azure rejects parallel deployment creates on the same account, so we serialize
# them with a per-resource depends_on chain via for_each ordering on a sorted key.
# ---------------------------------------------------------------------------
resource "azurerm_cognitive_deployment" "model" {
  for_each = var.model_deployments

  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.model_name
    version = each.value.model_version
  }

  scale {
    type     = "Standard"
    capacity = each.value.capacity
  }
}

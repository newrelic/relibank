terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "azurerm" {
  features {}
}

locals {
  account_name = "relibank-${var.demo_environment}-openai"

  # Normalize each assistant entry so optional fields have predictable defaults.
  # var.assistants is `any` to allow nested tool schemas to vary; defaults applied here.
  assistants_resolved = {
    for k, a in var.assistants : k => {
      name         = a.name
      instructions = a.instructions
      model        = a.model
      temperature  = try(a.temperature, 1)
      top_p        = try(a.top_p, 1)
      tools        = try(a.tools, [])
      metadata     = try(a.metadata, {})
    }
  }
}

# ---------------------------------------------------------------------------
# Azure OpenAI (Cognitive Services) account — backs the legacy Assistants API.
# `custom_subdomain_name` is required so the dataplane Assistants endpoint is
# served at https://<subdomain>.openai.azure.com/.
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
# Model deployment that the assistants reference by `model` name.
# ---------------------------------------------------------------------------
resource "azurerm_cognitive_deployment" "model" {
  name                 = var.model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }

  scale {
    type     = "Standard"
    capacity = var.model_capacity
  }
}

# ---------------------------------------------------------------------------
# Assistants — created via the AOAI dataplane. No first-class TF resource
# exists, so we drive it from a `terraform_data` + `local-exec` upsert script.
# Re-runs on any change to name/instructions/model/temperature/top_p/tools.
# ---------------------------------------------------------------------------
resource "terraform_data" "assistant" {
  for_each = local.assistants_resolved

  triggers_replace = {
    name         = each.value.name
    instructions = each.value.instructions
    model        = each.value.model
    temperature  = each.value.temperature
    top_p        = each.value.top_p
    tools        = jsonencode(each.value.tools)
    metadata     = jsonencode(each.value.metadata)
    endpoint     = azurerm_cognitive_account.openai.endpoint
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/upsert-assistant.sh"
    environment = {
      AOAI_ENDPOINT = azurerm_cognitive_account.openai.endpoint
      AOAI_API_KEY  = azurerm_cognitive_account.openai.primary_access_key
      ASSISTANT_BODY = jsonencode({
        name         = each.value.name
        instructions = each.value.instructions
        model        = each.value.model
        temperature  = each.value.temperature
        top_p        = each.value.top_p
        tools        = each.value.tools
        metadata     = each.value.metadata
      })
      OUTPUT_FILE = "${path.module}/.assistants/${each.key}.id"
    }
  }

  provisioner "local-exec" {
    when    = destroy
    command = "${path.module}/scripts/delete-assistant.sh"
    environment = {
      AOAI_ENDPOINT = self.triggers_replace.endpoint
      OUTPUT_FILE   = "${path.module}/.assistants/${each.key}.id"
    }
  }

  depends_on = [azurerm_cognitive_deployment.model]
}

# ---------------------------------------------------------------------------
# Read each assistant ID back so it can flow through outputs.
# ---------------------------------------------------------------------------
data "local_file" "assistant_id" {
  for_each = local.assistants_resolved
  filename = "${path.module}/.assistants/${each.key}.id"

  depends_on = [terraform_data.assistant]
}

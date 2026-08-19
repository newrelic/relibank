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
  # Storage account names: lowercase alphanumeric only, ≤24 chars.
  storage_account_name = substr(replace("relibank${var.demo_environment}fn", "-", ""), 0, 24)
  function_app_name    = "relibank-${var.demo_environment}-notifications-fn"
  plan_name            = "relibank-${var.demo_environment}-asp"
  acs_name             = "relibank-${var.demo_environment}-acs"
  email_service_name   = "relibank-${var.demo_environment}-email"

  log_analytics_workspace_name = "relibank-${var.demo_environment}-notifications-law"
  appinsights_name             = "relibank-${var.demo_environment}-notifications-ai"

  common_tags = {
    team           = "ReliBank - Platform"
    deploymentTier = var.demo_environment
    heroChannel    = "help-relibank-platform"
    managedBy      = "terraform"
    appStack       = "relibank"
    githubRepo     = "https://github.com/newrelic/relibank"
  }
}

# ---------------------------------------------------------------------------
# Storage account — required runtime backing for Function App
# ---------------------------------------------------------------------------
resource "azurerm_storage_account" "fn" {
  name                     = local.storage_account_name
  resource_group_name      = var.aks_resource_group
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"

  tags = merge(local.common_tags, {
    purpose = "notifications-function-runtime"
  })
}

# ---------------------------------------------------------------------------
# App Service Plan — FlexConsumption (FC1) by default, matches prod.
# ---------------------------------------------------------------------------
resource "azurerm_service_plan" "fn" {
  name                = local.plan_name
  resource_group_name = var.aks_resource_group
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.function_plan_sku

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Azure Communication Services — provides email + SMS clients to the function.
# ---------------------------------------------------------------------------
resource "azurerm_communication_service" "acs" {
  name                = local.acs_name
  resource_group_name = var.aks_resource_group
  data_location       = "United States"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Email Communication Service + auto-managed subdomain.
# ---------------------------------------------------------------------------
resource "azurerm_email_communication_service" "email" {
  name                = local.email_service_name
  resource_group_name = var.aks_resource_group
  data_location       = "United States"

  tags = local.common_tags
}

resource "azurerm_email_communication_service_domain" "email" {
  name              = "AzureManagedDomain"
  email_service_id  = azurerm_email_communication_service.email.id
  domain_management = "AzureManaged"
}

# ---------------------------------------------------------------------------
# Bind the email domain to the ACS resource so the Email SDK can use it.
# ---------------------------------------------------------------------------
resource "azurerm_communication_service_email_domain_association" "this" {
  communication_service_id = azurerm_communication_service.acs.id
  email_service_domain_id  = azurerm_email_communication_service_domain.email.id
}

# ---------------------------------------------------------------------------
# Log Analytics workspace + Application Insights — required for the Function
# App to generate invocation-level telemetry (execution counts, HTTP error
# metrics). Without this, memory/status metrics still work (they come from
# the host directly), but functionExecutionCount/http5xx never populate in
# Azure Monitor at all, regardless of real traffic — confirmed by querying
# Azure Monitor's metrics API directly. Workspace-based mode is required;
# the classic standalone Application Insights mode is being phased out.
# ---------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "notifications" {
  name                = local.log_analytics_workspace_name
  resource_group_name = var.aks_resource_group
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

resource "azurerm_application_insights" "notifications" {
  name                = local.appinsights_name
  resource_group_name = var.aks_resource_group
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.notifications.id
  application_type    = "web"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Linux Python Function App — runtime that hosts notify_user_trigger.
# ---------------------------------------------------------------------------
resource "azurerm_linux_function_app" "notifications" {
  name                       = local.function_app_name
  resource_group_name        = var.aks_resource_group
  location                   = var.location
  service_plan_id            = azurerm_service_plan.fn.id
  storage_account_name       = azurerm_storage_account.fn.name
  storage_account_access_key = azurerm_storage_account.fn.primary_access_key

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    AZURE_ACS_CONNECTION_STRING           = azurerm_communication_service.acs.primary_connection_string
    AZURE_ACS_EMAIL_SENDER                = "DoNotReply@${azurerm_email_communication_service_domain.email.mail_from_sender_domain}"
    AZURE_ACS_SMS_SENDER                  = var.sms_sender_phone
    SMS_THROTTLE_PERCENTAGE               = tostring(var.sms_throttle_percentage)
    SIMULATE_NOTIFICATIONS                = tostring(var.simulate_notifications)
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.notifications.connection_string
    FUNCTIONS_EXTENSION_VERSION           = "~4"
    # Linux Consumption (Y1) needs these set explicitly for `func azure functionapp publish`
    # to perform a remote build during deployment. Without them, the publish step succeeds
    # silently but the function never registers.
    SCM_DO_BUILD_DURING_DEPLOYMENT = "1"
    ENABLE_ORYX_BUILD              = "true"
  }

  tags = local.common_tags

  depends_on = [
    azurerm_communication_service_email_domain_association.this,
  ]
}

# ---------------------------------------------------------------------------
# Function host keys — needed to construct the FUNCTION-auth-level URL.
# ---------------------------------------------------------------------------
data "azurerm_function_app_host_keys" "notifications" {
  name                = azurerm_linux_function_app.notifications.name
  resource_group_name = var.aks_resource_group

  depends_on = [azurerm_linux_function_app.notifications]
}

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.36.0"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_kubernetes_cluster" "cluster" {
  name                = var.aks_cluster_name
  resource_group_name = var.aks_resource_group
}

provider "kubernetes" {
  host                   = data.azurerm_kubernetes_cluster.cluster.kube_config[0].host
  client_certificate     = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].client_certificate)
  client_key             = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].client_key)
  cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].cluster_ca_certificate)
}

# AOAI account, model deployment, and assistants are owned by terraform/aks/ai_services
# and must be applied for this env before this module runs.
data "terraform_remote_state" "ai_services" {
  backend = "azurerm"
  config = {
    resource_group_name  = "ReliBank"
    storage_account_name = var.tf_state_storage_account
    container_name       = var.tf_state_container
    key                  = "relibank/${var.demo_environment}/ai_services.tfstate"
  }
}

# Notifications Function App + ACS owned by terraform/aks/notifications.
# Must be applied (and function code published) for this env before this module runs.
data "terraform_remote_state" "notifications" {
  backend = "azurerm"
  config = {
    resource_group_name  = "ReliBank"
    storage_account_name = var.tf_state_storage_account
    container_name       = var.tf_state_container
    key                  = "relibank/${var.demo_environment}/notifications.tfstate"
  }
}

module "relibank_green" {
  source = "../app_module"

  demo_environment          = var.demo_environment
  target_color              = "green"
  aks_cluster_name          = var.aks_cluster_name
  aks_resource_group        = var.aks_resource_group
  acr_server                = var.acr_server
  mssql_sa_password         = var.mssql_sa_password
  mssql_sa_user             = var.mssql_sa_user
  postgres_password         = var.postgres_password
  postgres_user             = var.postgres_user
  azure_openai_endpoint     = data.terraform_remote_state.ai_services.outputs.endpoint
  azure_openai_api_key      = data.terraform_remote_state.ai_services.outputs.api_key
  assistant_b_delay_seconds = var.assistant_b_delay_seconds
  azure_function_url        = data.terraform_remote_state.notifications.outputs.function_url
}

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

module "relibank_blue" {
  source = "../app_module"

  demo_environment      = var.demo_environment
  target_color          = "blue"
  aks_cluster_name      = var.aks_cluster_name
  aks_resource_group    = var.aks_resource_group
  acr_server            = var.acr_server
  mssql_sa_password     = var.mssql_sa_password
  mssql_sa_user         = var.mssql_sa_user
  postgres_password     = var.postgres_password
  postgres_user         = var.postgres_user
  azure_openai_endpoint = var.azure_openai_endpoint
  azure_openai_api_key  = var.azure_openai_api_key
}

# New Relic entity management for ReliBank
#
# Mirrors demogorgon's `applications/microservices-demo/terraform/newrelic/newrelic/` pattern:
# one file per NR entity type, NerdGraph CRUD via the newrelic/newrelic provider, env-scoped state.
#
# This module is the third layer of the ReliBank deployer:
#   infra (relibank-infra.yml) -> app (deploy-relibank.yml) -> new relic (relibank-newrelic.yml)
#
# Entity data sources (nr_entities.tf) resolve real APM/Browser entities by name, which means
# this module's `terraform apply` requires that the app tier has been deployed at least once
# and services are reporting to NR. See docs/deployer/runbook.md for the ordering.
#
# The module also installs the cluster-side NR observability stack (nri-bundle + nr-ebpf-agent)
# via helm — see nr_infra_agent.tf. The `newrelic` namespace itself is created by the infra
# tier (terraform/aks/infra/main.tf) and merely referenced here.

terraform {
  required_providers {
    newrelic = {
      source  = "newrelic/newrelic"
      version = "~> 3.61"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.36.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "newrelic" {
  account_id = var.new_relic_account_id
  api_key    = var.new_relic_user_api_key
  region     = var.new_relic_region # Valid regions: US, EU
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

provider "helm" {
  kubernetes {
    host                   = data.azurerm_kubernetes_cluster.cluster.kube_config[0].host
    client_certificate     = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].client_certificate)
    client_key             = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].client_key)
    cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].cluster_ca_certificate)
  }
}

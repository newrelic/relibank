# terraform/aks/cluster/main.tf
# Creates the AKS cluster and its resource group for one environment.
# Equivalent to demogorgon's terraform/eks/init/ stage.
#
# Run once per environment before any app deployments.

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

# ---------------------------------------------------------------------------
# Resource group — pre-existing, created by setup-environment.sh
# ---------------------------------------------------------------------------
data "azurerm_resource_group" "relibank_env" {
  name = var.resource_group_name
}

# ---------------------------------------------------------------------------
# Resolve the latest GA Kubernetes version available in the target region
# (avoids LTS-only versions like 1.32.x that require Premium tier)
# ---------------------------------------------------------------------------
data "azurerm_kubernetes_service_versions" "current" {
  location        = var.location
  include_preview = false
}

# ---------------------------------------------------------------------------
# AKS cluster — system node pool only; color node pools added by app_module
# ---------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "relibank" {
  name                = var.aks_cluster_name
  location            = var.location
  resource_group_name = data.azurerm_resource_group.relibank_env.name
  dns_prefix          = var.aks_cluster_name
  kubernetes_version  = coalesce(var.kubernetes_version, data.azurerm_kubernetes_service_versions.current.latest_version)

  # OIDC issuer is auto-enabled by Azure for new clusters and cannot be turned off.
  # Pin it here so TF state matches the cluster.
  oidc_issuer_enabled = true

  default_node_pool {
    name       = "system"
    node_count = 2
    vm_size    = "Standard_D2s_v3"

    node_labels = {
      "nodepool-type" = "system"
      "environment"   = var.demo_environment
    }

    # Pin Azure's auto-injected upgrade defaults so TF doesn't churn.
    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    environment = var.demo_environment
    managed_by  = "terraform"
  }
}

# ---------------------------------------------------------------------------
# ACR pull — lets the cluster's kubelet identity pull from the environment ACR
# ---------------------------------------------------------------------------
data "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = data.azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.relibank.kubelet_identity[0].object_id
}

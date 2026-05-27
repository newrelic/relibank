# terraform/aks/infra/main.tf
# Installs cluster-wide components onto an existing AKS cluster.
# Equivalent to demogorgon's terraform/eks/infra/ stage.
#
# Installs:
#   - NGINX Ingress Controller (replaces demogorgon's ALB controller)
#   - newrelic namespace
#   - relibank namespace (shared databases / Kafka live here)
#
# Run after cluster/ is applied and before any color deployments.

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
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
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

provider "helm" {
  kubernetes {
    host                   = data.azurerm_kubernetes_cluster.cluster.kube_config[0].host
    client_certificate     = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].client_certificate)
    client_key             = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].client_key)
    cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.cluster.kube_config[0].cluster_ca_certificate)
  }
}

# ---------------------------------------------------------------------------
# NGINX Ingress Controller
# Replaces demogorgon's ALB controller. Provisions an Azure Load Balancer
# automatically via the LoadBalancer service type.
# ---------------------------------------------------------------------------
resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  wait             = true
  timeout          = 300

  set {
    name  = "controller.service.type"
    value = "LoadBalancer"
  }

  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/azure-load-balancer-health-probe-request-path"
    value = "/healthz"
  }
}

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

# Shared app namespace — databases and Kafka live here (not color-specific)
resource "kubernetes_namespace_v1" "relibank" {
  metadata {
    name = "relibank"
    labels = {
      environment = var.demo_environment
      app         = "relibank"
    }
  }
}

# New Relic namespace — used by nri-bundle Helm chart
resource "kubernetes_namespace_v1" "newrelic" {
  metadata {
    name = "newrelic"
    labels = {
      environment = var.demo_environment
      app         = "newrelic"
    }
  }
}

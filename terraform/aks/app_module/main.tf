# app_module/main.tf
# Reusable module instantiated for each blue/green color deployment.
# Creates: AKS node pool, K8s namespace, ConfigMap, Secret, and all service Deployments + Services.
#
# All services are driven by the var.services map — see variables.tf for the full inventory.
# To add a service: add an entry to var.services. To customize per-environment: override the
# services variable from the caller.

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

# --- Look up the AKS cluster to get its ID ---
data "azurerm_kubernetes_cluster" "cluster" {
  name                = var.aks_cluster_name
  resource_group_name = var.aks_resource_group
}

# --- AKS Node Pool for this color ---
# Node pool name max 12 chars, lowercase alphanumeric only
resource "azurerm_kubernetes_cluster_node_pool" "relibank_color_np" {
  name                  = var.target_color
  kubernetes_cluster_id = data.azurerm_kubernetes_cluster.cluster.id
  vm_size               = "Standard_D2s_v3"
  node_count            = 3

  node_labels = {
    "node-color"  = var.target_color
    "environment" = var.demo_environment
    "app"         = "relibank"
  }

  lifecycle {
    ignore_changes = [node_count]
  }
}

# --- Kubernetes Namespace for this color ---
resource "kubernetes_namespace_v1" "relibank_color" {
  metadata {
    name = "relibank-${var.target_color}"
    labels = {
      environment = var.demo_environment
      color       = var.target_color
    }
  }
}

locals {
  ns = kubernetes_namespace_v1.relibank_color.metadata[0].name

  # Overlay runtime-computed env vars (e.g. LOCUST_HOST from var.locust_host) into the
  # services map. Default values can't reference other variables, so we merge them here.
  services_resolved = {
    for name, svc in var.services : name => merge(svc, {
      extra_envs = name == "scenario-runner-service" ? merge(svc.extra_envs, { LOCUST_HOST = var.locust_host }) : svc.extra_envs
    })
  }
}

# --- Infrastructure ConfigMap ---
# Uses FQDNs for shared infra (databases, kafka) in the relibank namespace
resource "kubernetes_config_map_v1" "infrastructure_config" {
  metadata {
    name      = "infrastructure-config"
    namespace = local.ns
  }

  data = {
    MSSQL_DATABASE_NAME         = "RelibankDB"
    MSSQL_SERVER_NAME           = "mssql-0.relibank.svc.cluster.local"
    MSSQL_PORT                  = "1433"
    POSTGRES_DATABASE_NAME      = "accountsdb"
    POSTGRES_SERVER_NAME        = "accounts-db.relibank.svc.cluster.local"
    POSTGRES_PORT               = "5432"
    KAFKA_BROKER                = "kafka.relibank.svc.cluster.local:29092"
    KAFKA_INTERNAL_PORT         = "29092"
    KAFKA_EXTERNAL_PORT         = "9092"
    KAFKA_SERVER_NAME           = "kafka.relibank.svc.cluster.local"
    ZOOKEEPER_SERVER_NAME       = "zookeeper.relibank.svc.cluster.local"
    ZOOKEEPER_PORT              = "2181"
    TRANSACTION_SERVICE_URL     = "http://transaction-service:5001"
    ACCOUNTS_SERVICE_URL        = "http://accounts-service:5002"
    AUTH_SERVICE_URL            = "http://auth-service:5002"
    BILL_PAY_SERVICE_URL        = "http://bill-pay-service:5000"
    SUPPORT_SERVICE_URL         = "http://support-service:5003"
    SCHEDULER_SERVICE_URL       = "http://scheduler-service:5004"
    SCENARIO_RUNNER_SERVICE_URL = "http://scenario-runner-service:8000"
  }

  depends_on = [kubernetes_namespace_v1.relibank_color]
}

# --- Database Credentials Secret ---
resource "kubernetes_secret_v1" "database_credentials" {
  metadata {
    name      = "database-credentials"
    namespace = local.ns
  }

  data = {
    MSSQL_SA_PASSWORD = var.mssql_sa_password
    MSSQL_SA_USER     = var.mssql_sa_user
    POSTGRES_PASSWORD = var.postgres_password
    POSTGRES_USER     = var.postgres_user
  }

  type       = "Opaque"
  depends_on = [kubernetes_namespace_v1.relibank_color]
}

# ==========================================
# Per-service Deployments + Services
# ==========================================

resource "kubernetes_deployment_v1" "service" {
  for_each = local.services_resolved

  metadata {
    name      = each.key
    namespace = local.ns
    labels    = { app = each.key, version = var.target_color }
  }

  spec {
    replicas = each.value.replicas

    selector {
      match_labels = { app = each.key, version = var.target_color }
    }

    template {
      metadata {
        labels = { app = each.key, version = var.target_color }
      }

      spec {
        node_selector = { "node-color" = var.target_color }

        container {
          name  = each.key
          image = "${var.acr_server}/${each.value.image}:${var.target_color}"

          port {
            container_port = each.value.container_port
          }

          dynamic "resources" {
            for_each = each.value.cpu_request != null ? [1] : []
            content {
              requests = {
                cpu    = each.value.cpu_request
                memory = each.value.memory_request
              }
              limits = {
                cpu    = each.value.cpu_limit
                memory = each.value.memory_limit
              }
            }
          }

          dynamic "env" {
            for_each = each.value.config_map_envs
            content {
              name = env.key
              value_from {
                config_map_key_ref {
                  name = "infrastructure-config"
                  key  = env.value
                }
              }
            }
          }

          dynamic "env" {
            for_each = each.value.secret_envs
            content {
              name = env.key
              value_from {
                secret_key_ref {
                  name = "database-credentials"
                  key  = env.value
                }
              }
            }
          }

          dynamic "env" {
            for_each = each.value.extra_envs
            content {
              name  = env.key
              value = env.value
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_config_map_v1.infrastructure_config,
    kubernetes_secret_v1.database_credentials,
    azurerm_kubernetes_cluster_node_pool.relibank_color_np,
  ]
}

resource "kubernetes_service_v1" "service" {
  for_each = local.services_resolved

  metadata {
    name      = each.key
    namespace = local.ns
  }

  spec {
    selector = { app = each.key, version = var.target_color }
    port {
      port        = each.value.service_port
      target_port = each.value.container_port
    }
  }
}

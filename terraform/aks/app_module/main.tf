# app_module/main.tf
# Reusable module instantiated for each blue/green color deployment.
# Creates: AKS node pool, K8s namespace, ConfigMap, Secret, and all 10 service Deployments + Services.

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
# FRONTEND SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "frontend_service" {
  metadata {
    name      = "frontend-service"
    namespace = local.ns
    labels    = { app = "frontend-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "frontend-service", version = var.target_color } }
    template {
      metadata { labels = { app = "frontend-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "frontend-service"
          image = "${var.acr_server}/frontend-service:${var.target_color}"
          port { container_port = 3000 }
          resources {
            requests = { cpu = "1000m", memory = "1Gi" }
            limits   = { cpu = "2000m", memory = "2Gi" }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_namespace_v1.relibank_color, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "frontend_service" {
  metadata {
    name      = "frontend-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "frontend-service", version = var.target_color }
    port { name = "http", port = 3000, target_port = 3000 }
  }
}

# ==========================================
# ACCOUNTS SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "accounts_service" {
  metadata {
    name      = "accounts-service"
    namespace = local.ns
    labels    = { app = "accounts-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "accounts-service", version = var.target_color } }
    template {
      metadata { labels = { app = "accounts-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "accounts-service"
          image = "${var.acr_server}/accounts-service:${var.target_color}"
          port { container_port = 5000 }
          env {
            name = "DB_HOST"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "POSTGRES_SERVER_NAME" } }
          }
          env {
            name = "DB_NAME"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "POSTGRES_DATABASE_NAME" } }
          }
          env {
            name = "DB_PASSWORD"
            value_from { secret_key_ref { name = "database-credentials", key = "POSTGRES_PASSWORD" } }
          }
          env {
            name = "DB_USER"
            value_from { secret_key_ref { name = "database-credentials", key = "POSTGRES_USER" } }
          }
          env {
            name = "TRANSACTION_SERVICE_URL"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "TRANSACTION_SERVICE_URL" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, kubernetes_secret_v1.database_credentials, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "accounts_service" {
  metadata {
    name      = "accounts-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "accounts-service", version = var.target_color }
    port { name = "5002", port = 5002, target_port = 5000 }
  }
}

# ==========================================
# AUTH SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "auth_service" {
  metadata {
    name      = "auth-service"
    namespace = local.ns
    labels    = { app = "auth-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "auth-service", version = var.target_color } }
    template {
      metadata { labels = { app = "auth-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "auth-service"
          image = "${var.acr_server}/auth-service:${var.target_color}"
          port { container_port = 5002 }
          env {
            name = "DB_HOST"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "POSTGRES_SERVER_NAME" } }
          }
          env {
            name = "DB_NAME"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "POSTGRES_DATABASE_NAME" } }
          }
          env {
            name = "DB_PASSWORD"
            value_from { secret_key_ref { name = "database-credentials", key = "POSTGRES_PASSWORD" } }
          }
          env {
            name = "DB_USER"
            value_from { secret_key_ref { name = "database-credentials", key = "POSTGRES_USER" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, kubernetes_secret_v1.database_credentials, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "auth_service" {
  metadata {
    name      = "auth-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "auth-service", version = var.target_color }
    port { name = "5002", port = 5002, target_port = 5002 }
  }
}

# ==========================================
# TRANSACTION SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "transaction_service" {
  metadata {
    name      = "transaction-service"
    namespace = local.ns
    labels    = { app = "transaction-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "transaction-service", version = var.target_color } }
    template {
      metadata { labels = { app = "transaction-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "transaction-service"
          image = "${var.acr_server}/transaction-service:${var.target_color}"
          port { container_port = 5000 }
          env {
            name = "DB_DATABASE"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "MSSQL_DATABASE_NAME" } }
          }
          env {
            name = "DB_PASSWORD"
            value_from { secret_key_ref { name = "database-credentials", key = "MSSQL_SA_PASSWORD" } }
          }
          env {
            name = "DB_SERVER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "MSSQL_SERVER_NAME" } }
          }
          env {
            name = "DB_USERNAME"
            value_from { secret_key_ref { name = "database-credentials", key = "MSSQL_SA_USER" } }
          }
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, kubernetes_secret_v1.database_credentials, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "transaction_service" {
  metadata {
    name      = "transaction-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "transaction-service", version = var.target_color }
    port { name = "5001", port = 5001, target_port = 5000 }
  }
}

# ==========================================
# BILL PAY SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "bill_pay_service" {
  metadata {
    name      = "bill-pay-service"
    namespace = local.ns
    labels    = { app = "bill-pay-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "bill-pay-service", version = var.target_color } }
    template {
      metadata { labels = { app = "bill-pay-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "bill-pay-service"
          image = "${var.acr_server}/bill-pay-service:${var.target_color}"
          port { container_port = 5000 }
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
          env {
            name = "TRANSACTION_SERVICE_URL"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "TRANSACTION_SERVICE_URL" } }
          }
          env {
            name = "SCENARIO_SERVICE_URL"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "SCENARIO_RUNNER_SERVICE_URL" } }
          }
          env {
            name = "ACCOUNTS_SERVICE_URL"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "ACCOUNTS_SERVICE_URL" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "bill_pay_service" {
  metadata {
    name      = "bill-pay-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "bill-pay-service", version = var.target_color }
    port { name = "5000", port = 5000, target_port = 5000 }
  }
}

# ==========================================
# SUPPORT SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "support_service" {
  metadata {
    name      = "support-service"
    namespace = local.ns
    labels    = { app = "support-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "support-service", version = var.target_color } }
    template {
      metadata { labels = { app = "support-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "support-service"
          image = "${var.acr_server}/support-service:${var.target_color}"
          port { container_port = 5003 }
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "support_service" {
  metadata {
    name      = "support-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "support-service", version = var.target_color }
    port { name = "5003", port = 5003, target_port = 5003 }
  }
}

# ==========================================
# RISK ASSESSMENT SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "risk_assessment_service" {
  metadata {
    name      = "risk-assessment-service"
    namespace = local.ns
    labels    = { app = "risk-assessment-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "risk-assessment-service", version = var.target_color } }
    template {
      metadata { labels = { app = "risk-assessment-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "risk-assessment-service"
          image = "${var.acr_server}/risk-assessment-service:${var.target_color}"
          port { container_port = 5001 }
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "risk_assessment_service" {
  metadata {
    name      = "risk-assessment-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "risk-assessment-service", version = var.target_color }
    port { name = "5001", port = 5001, target_port = 5001 }
  }
}

# ==========================================
# NOTIFICATIONS SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "notifications_service" {
  metadata {
    name      = "notifications-service"
    namespace = local.ns
    labels    = { app = "notifications-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "notifications-service", version = var.target_color } }
    template {
      metadata { labels = { app = "notifications-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "notifications-service"
          image = "${var.acr_server}/notifications-service:${var.target_color}"
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "notifications_service" {
  metadata {
    name      = "notifications-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "notifications-service", version = var.target_color }
    port { name = "5000", port = 5000, target_port = 5000 }
  }
}

# ==========================================
# SCHEDULER SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "scheduler_service" {
  metadata {
    name      = "scheduler-service"
    namespace = local.ns
    labels    = { app = "scheduler-service", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "scheduler-service", version = var.target_color } }
    template {
      metadata { labels = { app = "scheduler-service", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "scheduler-service"
          image = "${var.acr_server}/scheduler-service:${var.target_color}"
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
          env {
            name = "DB_SERVER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "MSSQL_SERVER_NAME" } }
          }
          env {
            name = "DB_DATABASE"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "MSSQL_DATABASE_NAME" } }
          }
          env {
            name = "DB_USERNAME"
            value_from { secret_key_ref { name = "database-credentials", key = "MSSQL_SA_USER" } }
          }
          env {
            name = "DB_PASSWORD"
            value_from { secret_key_ref { name = "database-credentials", key = "MSSQL_SA_PASSWORD" } }
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, kubernetes_secret_v1.database_credentials, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "scheduler_service" {
  metadata {
    name      = "scheduler-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "scheduler-service", version = var.target_color }
    port { name = "5004", port = 5004, target_port = 5000 }
  }
}

# ==========================================
# SCENARIO RUNNER SERVICE
# ==========================================
resource "kubernetes_deployment_v1" "scenario_runner_service" {
  metadata {
    name      = "scenario-runner-service"
    namespace = local.ns
    labels    = { app = "scenario-runner", version = var.target_color }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "scenario-runner", version = var.target_color } }
    template {
      metadata { labels = { app = "scenario-runner", version = var.target_color } }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "scenario-runner-service"
          image = "${var.acr_server}/scenario-runner:${var.target_color}"
          port { container_port = 8000 }
          env {
            name = "KAFKA_BROKER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "KAFKA_BROKER" } }
          }
          env {
            name = "DB_SERVER"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "MSSQL_SERVER_NAME" } }
          }
          env {
            name = "DB_DATABASE"
            value_from { config_map_key_ref { name = "infrastructure-config", key = "MSSQL_DATABASE_NAME" } }
          }
          env {
            name = "DB_USERNAME"
            value_from { secret_key_ref { name = "database-credentials", key = "MSSQL_SA_USER" } }
          }
          env {
            name = "DB_PASSWORD"
            value_from { secret_key_ref { name = "database-credentials", key = "MSSQL_SA_PASSWORD" } }
          }
          env {
            name  = "LOCUST_HOST"
            value = var.locust_host
          }
        }
      }
    }
  }
  depends_on = [kubernetes_config_map_v1.infrastructure_config, kubernetes_secret_v1.database_credentials, azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

resource "kubernetes_service_v1" "scenario_runner_service" {
  metadata {
    name      = "scenario-runner-service"
    namespace = local.ns
  }
  spec {
    selector = { app = "scenario-runner", version = var.target_color }
    port { port = 8000, target_port = 8000 }
  }
}

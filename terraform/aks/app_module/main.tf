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
# Short DNS names — all shared infra (DBs, Kafka, Zk) lives in the same color namespace
# as the apps, so service-name lookups resolve without FQDNs.
resource "kubernetes_config_map_v1" "infrastructure_config" {
  metadata {
    name      = "infrastructure-config"
    namespace = local.ns
  }

  data = {
    MSSQL_DATABASE_NAME         = "RelibankDB"
    MSSQL_SERVER_NAME           = "mssql"
    MSSQL_PORT                  = "1433"
    POSTGRES_DATABASE_NAME      = "accountsdb"
    POSTGRES_SERVER_NAME        = "accounts-db"
    POSTGRES_PORT               = "5432"
    KAFKA_BROKER                = "kafka:29092"
    KAFKA_INTERNAL_PORT         = "29092"
    KAFKA_EXTERNAL_PORT         = "9092"
    KAFKA_SERVER_NAME           = "kafka"
    ZOOKEEPER_SERVER_NAME       = "zookeeper"
    ZOOKEEPER_PORT              = "2181"
    TRANSACTION_SERVICE_URL     = "http://transaction-service:5001"
    ACCOUNTS_SERVICE_URL        = "http://accounts-service:5002"
    AUTH_SERVICE_URL            = "http://auth-service:5002"
    BILL_PAY_SERVICE_URL        = "http://bill-pay-service:5000"
    SUPPORT_SERVICE_URL         = "http://support-service:5003"
    SCHEDULER_SERVICE_URL       = "http://scheduler-service:5004"
    SCENARIO_RUNNER_SERVICE_URL = "http://scenario-runner-service:8000"
    AZURE_OPENAI_ENDPOINT       = var.azure_openai_endpoint
    ASSISTANT_B_DELAY_SECONDS   = tostring(var.assistant_b_delay_seconds)
  }

  depends_on = [kubernetes_namespace_v1.relibank_color]
}

# --- Service Credentials Secret ---
# Holds DB creds and the Azure OpenAI API key consumed by support-service.
resource "kubernetes_secret_v1" "database_credentials" {
  metadata {
    name      = "database-credentials"
    namespace = local.ns
  }

  data = {
    MSSQL_SA_PASSWORD    = var.mssql_sa_password
    MSSQL_SA_USER        = var.mssql_sa_user
    POSTGRES_PASSWORD    = var.postgres_password
    POSTGRES_USER        = var.postgres_user
    AZURE_OPENAI_API_KEY = var.azure_openai_api_key
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

# ==========================================
# Shared infra (per-color) — DBs, Kafka, Zookeeper, init jobs
# Mirrors demogorgon's pattern: each color gets its own data plane.
# ==========================================

# --- PostgreSQL PVC ---
resource "kubernetes_persistent_volume_claim_v1" "accounts_data" {
  metadata {
    name      = "accounts-data"
    namespace = local.ns
    labels    = { app = "accounts-db" }
  }
  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = { storage = "2Gi" }
    }
  }
  wait_until_bound = false
  depends_on       = [kubernetes_namespace_v1.relibank_color]
}

# --- MSSQL StatefulSet + headless Service ---
resource "kubernetes_service_v1" "mssql" {
  metadata {
    name      = "mssql"
    namespace = local.ns
    labels    = { app = "mssql" }
  }
  spec {
    cluster_ip = "None"
    selector   = { app = "mssql" }
    port {
      name        = "tcpsql"
      port        = 1433
      target_port = 1433
      protocol    = "TCP"
    }
  }
  depends_on = [kubernetes_namespace_v1.relibank_color]
}

resource "kubernetes_stateful_set_v1" "mssql" {
  metadata {
    name      = "mssql"
    namespace = local.ns
    labels    = { app = "mssql" }
  }
  spec {
    service_name = kubernetes_service_v1.mssql.metadata[0].name
    replicas     = 1
    selector {
      match_labels = { app = "mssql" }
    }
    template {
      metadata {
        labels = { app = "mssql" }
      }
      spec {
        node_selector = { "node-color" = var.target_color }
        security_context {
          fs_group = 10001
        }
        termination_grace_period_seconds = 30
        container {
          name              = "mssql"
          image             = "${var.acr_server}/mssql-custom:${var.target_color}"
          image_pull_policy = "IfNotPresent"
          port {
            container_port = 1433
            name           = "tcpsql"
          }
          env {
            name  = "ACCEPT_EULA"
            value = "Y"
          }
          env {
            name  = "MSSQL_ENABLE_HADR"
            value = "1"
          }
          env {
            name  = "MSSQL_AGENT_ENABLED"
            value = "1"
          }
          env {
            name  = "MSSQL_MEMORY_LIMIT_MB"
            value = "6144"
          }
          env {
            name  = "MSSQL_PID"
            value = "Developer"
          }
          env {
            name = "MSSQL_SA_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "MSSQL_SA_PASSWORD"
              }
            }
          }
          resources {
            requests = { cpu = "500m", memory = "1Gi" }
            limits   = { cpu = "1000m", memory = "2Gi" }
          }
          volume_mount {
            name       = "mssql"
            mount_path = "/var/opt/mssql"
          }
          liveness_probe {
            tcp_socket { port = "1433" }
            initial_delay_seconds = 60
            period_seconds        = 20
            timeout_seconds       = 10
          }
          readiness_probe {
            tcp_socket { port = "1433" }
            initial_delay_seconds = 45
            period_seconds        = 10
            timeout_seconds       = 5
          }
        }
      }
    }
    volume_claim_template {
      metadata {
        name = "mssql"
      }
      spec {
        access_modes = ["ReadWriteOnce"]
        resources {
          requests = { storage = "2Gi" }
        }
      }
    }
  }
  depends_on = [
    kubernetes_secret_v1.database_credentials,
    azurerm_kubernetes_cluster_node_pool.relibank_color_np,
  ]
}

# --- PostgreSQL (accounts-db) Deployment + Service ---
resource "kubernetes_service_v1" "accounts_db" {
  metadata {
    name      = "accounts-db"
    namespace = local.ns
    labels    = { app = "accounts-db" }
  }
  spec {
    selector = { app = "accounts-db" }
    port {
      name        = "5432"
      port        = 5432
      target_port = 5432
      protocol    = "TCP"
    }
  }
  depends_on = [kubernetes_namespace_v1.relibank_color]
}

resource "kubernetes_deployment_v1" "accounts_db" {
  metadata {
    name      = "accounts-db"
    namespace = local.ns
    labels    = { app = "accounts-db" }
  }
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "accounts-db" }
    }
    template {
      metadata {
        labels = { app = "accounts-db" }
      }
      spec {
        node_selector = { "node-color" = var.target_color }
        container {
          name  = "accounts-db"
          image = "${var.acr_server}/postgres-custom:${var.target_color}"
          port {
            container_port = 5432
            protocol       = "TCP"
          }
          env {
            name  = "POSTGRES_DB"
            value = "accountsdb"
          }
          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }
          env {
            name = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "POSTGRES_USER"
              }
            }
          }
          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }
          volume_mount {
            name       = "postgres-storage"
            mount_path = "/var/lib/postgresql/data"
          }
          liveness_probe {
            exec {
              command = ["pg_isready", "-U", "postgres"]
            }
            initial_delay_seconds = 30
            timeout_seconds       = 5
          }
          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "postgres"]
            }
            initial_delay_seconds = 5
            timeout_seconds       = 1
          }
        }
        volume {
          name = "postgres-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.accounts_data.metadata[0].name
          }
        }
      }
    }
  }
  depends_on = [
    kubernetes_secret_v1.database_credentials,
    kubernetes_persistent_volume_claim_v1.accounts_data,
    azurerm_kubernetes_cluster_node_pool.relibank_color_np,
  ]
}

# --- Zookeeper Deployment + Service ---
resource "kubernetes_service_v1" "zookeeper" {
  metadata {
    name      = "zookeeper"
    namespace = local.ns
    labels    = { app = "zookeeper" }
  }
  spec {
    selector = { app = "zookeeper" }
    port {
      name        = "2181"
      port        = 2181
      target_port = 2181
    }
  }
  depends_on = [kubernetes_namespace_v1.relibank_color]
}

resource "kubernetes_deployment_v1" "zookeeper" {
  metadata {
    name      = "zookeeper"
    namespace = local.ns
    labels    = { app = "zookeeper" }
  }
  spec {
    replicas = 1
    selector {
      match_labels = { app = "zookeeper" }
    }
    template {
      metadata {
        labels = { app = "zookeeper" }
      }
      spec {
        node_selector = { "node-color" = var.target_color }
        hostname      = "zookeeper"
        container {
          name  = "zookeeper"
          image = "bitnamilegacy/zookeeper:3.8"
          port {
            container_port = 2181
            protocol       = "TCP"
          }
          env {
            name  = "ALLOW_ANONYMOUS_LOGIN"
            value = "yes"
          }
          env {
            name  = "ZOO_MY_ID"
            value = "1"
          }
        }
      }
    }
  }
  depends_on = [azurerm_kubernetes_cluster_node_pool.relibank_color_np]
}

# --- Kafka Deployment + Service ---
resource "kubernetes_service_v1" "kafka" {
  metadata {
    name      = "kafka"
    namespace = local.ns
    labels    = { app = "kafka" }
  }
  spec {
    selector = { app = "kafka" }
    port {
      name        = "9092"
      port        = 9092
      target_port = 9092
    }
    port {
      name        = "29092"
      port        = 29092
      target_port = 29092
    }
    port {
      name        = "9999"
      port        = 9999
      target_port = 9999
    }
  }
  depends_on = [kubernetes_namespace_v1.relibank_color]
}

resource "kubernetes_deployment_v1" "kafka" {
  metadata {
    name      = "kafka"
    namespace = local.ns
    labels    = { app = "kafka" }
  }
  spec {
    replicas = 1
    selector {
      match_labels = { app = "kafka" }
    }
    template {
      metadata {
        labels = { app = "kafka" }
      }
      spec {
        node_selector = { "node-color" = var.target_color }
        hostname      = "kafka"
        container {
          name  = "kafka"
          image = "${var.acr_server}/kafka-with-monitoring:${var.target_color}"
          port {
            container_port = 9092
            protocol       = "TCP"
          }
          port {
            container_port = 29092
            protocol       = "TCP"
          }
          port {
            container_port = 9999
            name           = "jmx"
            protocol       = "TCP"
          }
          env {
            name  = "ALLOW_PLAINTEXT_LISTENER"
            value = "yes"
          }
          env {
            name  = "KAFKA_BROKER_ID"
            value = "1"
          }
          env {
            name  = "KAFKA_CFG_ADVERTISED_LISTENERS"
            value = "PLAINTEXT://kafka:29092,EXTERNAL://localhost:9092"
          }
          env {
            name  = "KAFKA_CFG_LISTENERS"
            value = "PLAINTEXT://:29092,EXTERNAL://:9092"
          }
          env {
            name  = "KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP"
            value = "PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT"
          }
          env {
            name  = "KAFKA_CFG_ZOOKEEPER_CONNECT"
            value = "zookeeper:2181"
          }
          env {
            name  = "KAFKA_JMX_OPTS"
            value = "-Dcom.sun.management.jmxremote=true -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false -Dcom.sun.management.jmxremote.port=9999 -Dcom.sun.management.jmxremote.rmi.port=9999 -Djava.rmi.server.hostname=kafka"
          }
          liveness_probe {
            tcp_socket { port = "9092" }
            failure_threshold = 5
            period_seconds    = 10
            timeout_seconds   = 5
          }
        }
      }
    }
  }
  depends_on = [
    kubernetes_service_v1.zookeeper,
    kubernetes_deployment_v1.zookeeper,
    azurerm_kubernetes_cluster_node_pool.relibank_color_np,
  ]
}

# --- MSSQL init Job ---
# Waits for MSSQL to be reachable, then runs /usr/config/init.sql baked into the image.
# Job is immutable post-apply; if you need to re-run, kubectl delete the job first.
resource "kubernetes_job_v1" "mssql_init" {
  metadata {
    name      = "mssql-init"
    namespace = local.ns
    labels    = { app = "mssql-init" }
  }
  spec {
    backoff_limit           = 3
    active_deadline_seconds = 900
    template {
      metadata {
        labels = { app = "mssql-init" }
      }
      spec {
        node_selector  = { "node-color" = var.target_color }
        restart_policy = "OnFailure"
        container {
          name              = "mssql-init"
          image             = "${var.acr_server}/mssql-custom:${var.target_color}"
          image_pull_policy = "IfNotPresent"
          command           = ["/bin/bash"]
          args = [
            "-c",
            "echo 'Waiting for MSSQL server to be ready...' && sleep 60 && echo 'Testing connection...' && until /opt/mssql-tools18/bin/sqlcmd -S $MSSQL_SERVER_NAME,$MSSQL_PORT -U \"$MSSQL_SA_USER\" -P \"$MSSQL_SA_PASSWORD\" -C -Q 'SELECT 1' -t 5; do echo 'MSSQL not ready, waiting...'; sleep 10; done && echo 'MSSQL is ready, running initialization...' && /opt/mssql-tools18/bin/sqlcmd -S $MSSQL_SERVER_NAME,$MSSQL_PORT -U \"$MSSQL_SA_USER\" -P \"$MSSQL_SA_PASSWORD\" -C -i /usr/config/init.sql && echo 'Database initialization completed successfully'"
          ]
          env {
            name = "MSSQL_SA_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "MSSQL_SA_PASSWORD"
              }
            }
          }
          env {
            name = "MSSQL_SA_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "MSSQL_SA_USER"
              }
            }
          }
          env {
            name = "MSSQL_SERVER_NAME"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map_v1.infrastructure_config.metadata[0].name
                key  = "MSSQL_SERVER_NAME"
              }
            }
          }
          env {
            name = "MSSQL_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map_v1.infrastructure_config.metadata[0].name
                key  = "MSSQL_PORT"
              }
            }
          }
          env {
            name = "MSSQL_DATABASE_NAME"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map_v1.infrastructure_config.metadata[0].name
                key  = "MSSQL_DATABASE_NAME"
              }
            }
          }
        }
      }
    }
  }
  wait_for_completion = false
  depends_on = [
    kubernetes_stateful_set_v1.mssql,
    kubernetes_service_v1.mssql,
  ]
}

# --- PostgreSQL init Job ---
resource "kubernetes_job_v1" "postgres_init" {
  metadata {
    name      = "postgres-init"
    namespace = local.ns
    labels    = { app = "postgres-init" }
  }
  spec {
    backoff_limit = 3
    template {
      metadata {
        labels = { app = "postgres-init" }
      }
      spec {
        node_selector  = { "node-color" = var.target_color }
        restart_policy = "OnFailure"
        container {
          name              = "postgres-init"
          image             = "${var.acr_server}/postgres-custom:${var.target_color}"
          image_pull_policy = "IfNotPresent"
          command           = ["/bin/bash"]
          args = [
            "-c",
            "echo 'Waiting for PostgreSQL server to be ready...' && sleep 30 && echo 'Connecting to PostgreSQL server...' && PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER_NAME -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DATABASE_NAME -f /docker-entrypoint-initdb.d/init.sql && echo 'Database initialization completed successfully'"
          ]
          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "POSTGRES_PASSWORD"
              }
            }
          }
          env {
            name = "POSTGRES_USER"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.database_credentials.metadata[0].name
                key  = "POSTGRES_USER"
              }
            }
          }
          env {
            name = "POSTGRES_SERVER_NAME"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map_v1.infrastructure_config.metadata[0].name
                key  = "POSTGRES_SERVER_NAME"
              }
            }
          }
          env {
            name = "POSTGRES_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map_v1.infrastructure_config.metadata[0].name
                key  = "POSTGRES_PORT"
              }
            }
          }
          env {
            name = "POSTGRES_DATABASE_NAME"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map_v1.infrastructure_config.metadata[0].name
                key  = "POSTGRES_DATABASE_NAME"
              }
            }
          }
        }
      }
    }
  }
  wait_for_completion = false
  depends_on = [
    kubernetes_deployment_v1.accounts_db,
    kubernetes_service_v1.accounts_db,
  ]
}

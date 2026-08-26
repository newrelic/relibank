# Cluster-side NR observability stack — a single nri-bundle helm release with infrastructure,
# kube-state-metrics, kubeEvents, logging, prometheus, and nr-ebpf-agent (nested subchart, for
# service-level workload metrics/logs, scoped to risk-assessment-service) all enabled.
locals {
  newrelic_namespace                        = "newrelic"
  new_relic_license_key_k8s_secret_key_name = "license_key"
}

resource "kubernetes_secret_v1" "newrelic_license" {
  metadata {
    name      = "newrelic-license"
    namespace = local.newrelic_namespace
  }
  data = {
    (local.new_relic_license_key_k8s_secret_key_name) = var.new_relic_license_key
  }
  type = "Opaque"
}

resource "helm_release" "nri_bundle" {
  name       = "newrelic-bundle"
  namespace  = local.newrelic_namespace
  repository = "https://helm-charts.newrelic.com"
  chart      = "nri-bundle"
  # Caret range (not an exact pin) so terraform always re-resolves against the repo index and
  # picks up new 8.x releases — pinning an exact version freezes state and stops tracking latest.
  version = "^8.0.0"
  wait    = true
  timeout = 800

  values = [
    yamlencode({
      global = {
        cluster                = var.aks_cluster_name
        customSecretName       = kubernetes_secret_v1.newrelic_license.metadata[0].name
        customSecretLicenseKey = local.new_relic_license_key_k8s_secret_key_name
        lowDataMode            = true
        region                 = var.new_relic_region
      }
      newrelic-infrastructure = {
        privileged = true
        integrations = {
          "nri-postgresql" = {
            discovery = {
              command = {
                exec = "/var/db/newrelic-infra/nri-discovery-kubernetes --tls --port 10250"
                match = {
                  "label.app" = "accounts-db"
                }
              }
            }
            integrations = [
              {
                name = "nri-postgresql"
                env = {
                  HOSTNAME                = "$${discovery.ip}"
                  PORT                    = 5432
                  USERNAME                = var.postgres_user
                  PASSWORD                = var.postgres_password
                  DATABASE                = "accountsdb"
                  COLLECTION_LIST         = "ALL"
                  ENABLE_QUERY_MONITORING = "true"
                  TIMEOUT                 = 10
                }
                interval         = "15s"
                labels           = { environment = var.demo_environment }
                inventory_source = "config/postgresql"
              }
            ]
          }
        }
      }
      ksm        = { enabled = true }
      kubeEvents = { enabled = true }
      logging    = { enabled = false }
      prometheus = { enabled = true }
      # nr-ebpf-agent: scoped to risk-assessment-service
      # (the one service intentionally left without APM auto-instrumentation)
      "nr-ebpf-agent" = {
        enabled              = true
        reportApmData        = "auto"
        reportNetworkMetrics = "auto"
        reportLogs           = "auto"
        allDataFilters = {
          dropNewRelicBundle = true
          keepNamespaces     = ["relibank-blue", "relibank-green"]
        }
        logDataFilters = {
          applicationLogReporting = {
            enabled                  = true
            keepStdStreamEntityRegex = "^risk-assessment-.*"
          }
        }
      }
    })
  ]
}

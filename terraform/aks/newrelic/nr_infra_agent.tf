# Cluster-side NR observability stack — installs:
#   1. nri-bundle helm chart with infrastructure, kube-state-metrics, kubeEvents, logging,
#      and prometheus integrations enabled.
#   2. nr-ebpf-agent helm chart for service-level Prometheus-style workload metrics.
# Mirrors demogorgon's eks_newrelic module. License key is created as a kubernetes_secret
# and passed to nri-bundle via customSecretName/customSecretLicenseKey to keep the license
# out of helm release values stored on the cluster.
#
# The `newrelic` namespace itself is created by the infra tier
# (terraform/aks/infra/main.tf, kubernetes_namespace_v1.newrelic). This module just installs
# into it.

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
  wait       = true
  timeout    = 800

  values = [
    yamlencode({
      global = {
        cluster                = var.aks_cluster_name
        customSecretName       = kubernetes_secret_v1.newrelic_license.metadata[0].name
        customSecretLicenseKey = local.new_relic_license_key_k8s_secret_key_name
        lowDataMode            = true
      }
      newrelic-infrastructure = {
        privileged = true
      }
      ksm        = { enabled = true }
      kubeEvents = { enabled = true }
      logging    = { enabled = true }
      prometheus = { enabled = true }
    })
  ]
}

# Companion: nr-ebpf-agent — service-level Prometheus-style metrics on workloads.
# Mirror of demogorgon's nr-ebpf-agent helm_release. Demogorgon pins to 1.1.0; we mirror.
# Installed with chart defaults (no allDataFilters) — demogorgon's filter config drops all
# services except authservice, which is demogorgon-specific. TMM can tune later if needed.
resource "helm_release" "nr_ebpf_agent" {
  name       = "nr-ebpf-agent"
  namespace  = local.newrelic_namespace
  repository = "https://helm-charts.newrelic.com"
  chart      = "nr-ebpf-agent"
  version    = "1.1.0"

  values = [
    yamlencode({
      global = {
        licenseKey = var.new_relic_license_key
        cluster    = var.aks_cluster_name
      }
    })
  ]

  depends_on = [helm_release.nri_bundle]
}

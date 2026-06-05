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

# Read the NGINX LB external IP — installed by relibank-infra.yml (Stage 2)
data "kubernetes_service_v1" "ingress_nginx" {
  metadata {
    name      = "ingress-nginx-controller"
    namespace = "ingress-nginx"
  }
}

locals {
  ingress_lb_ip = data.kubernetes_service_v1.ingress_nginx.status[0].load_balancer[0].ingress[0].ip
}

# A record: relibank-{env}.{dns_zone} → NGINX LB public IP
resource "azurerm_dns_a_record" "main" {
  name                = "relibank-${var.demo_environment}"
  zone_name           = var.dns_zone
  resource_group_name = var.dns_resource_group
  ttl                 = 300
  records             = [local.ingress_lb_ip]
}

# --- Main Ingress ---
# Routes all production traffic to the active color proxy service.
# Updating target_color and re-applying this module switches traffic.
resource "kubernetes_ingress_v1" "main_ingress" {
  wait_for_load_balancer = true

  metadata {
    name      = "main-ingress"
    namespace = "default"
    annotations = {
      "kubernetes.io/ingress.class" = "nginx"
    }
  }

  spec {
    rule {
      host = "relibank-${var.demo_environment}.${var.dns_zone}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "${var.target_color}-service"
              port { number = 80 }
            }
          }
        }
      }
    }
  }
}

# --- Header-based Test Ingress (Canary) ---
# Mirrors demogorgon's X-Test-Env header routing for pre-switch validation.
# Sends traffic with "X-Test-Env: {inactive_color}" header to the inactive color proxy,
# allowing validation of the new deployment before switching production traffic.
resource "kubernetes_ingress_v1" "canary_ingress" {
  metadata {
    name      = "canary-ingress"
    namespace = "default"
    annotations = {
      "kubernetes.io/ingress.class"                        = "nginx"
      "nginx.ingress.kubernetes.io/canary"                 = "true"
      "nginx.ingress.kubernetes.io/canary-by-header"       = "X-Test-Env"
      "nginx.ingress.kubernetes.io/canary-by-header-value" = local.inactive_color
    }
  }

  spec {
    rule {
      host = "relibank-${var.demo_environment}.${var.dns_zone}"
      http {
        path {
          path      = "/"
          path_type = "Prefix"
          backend {
            service {
              name = "${local.inactive_color}-service"
              port { number = 80 }
            }
          }
        }
      }
    }
  }

  # Only create canary ingress if the inactive color is deployed
  count = local.inactive_color == "blue" ? (local.blue_deployed ? 1 : 0) : (local.green_deployed ? 1 : 0)
}

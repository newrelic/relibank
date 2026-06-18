# NGINX Proxy for Blue
# Created as part of the blue deployment so it exists immediately.
# Lives in 'default' namespace; bridges the NGINX Ingress to services in relibank-blue namespace.

resource "kubernetes_config_map_v1" "blue_proxy_config" {
  metadata {
    name      = "blue-proxy-config"
    namespace = "default"
  }

  data = {
    "default.conf" = <<-EOF
    server {
        listen 80;
        # Use the internal Kubernetes DNS for service discovery
        resolver kube-dns.kube-system.svc.cluster.local valid=5s;

        location /bill-pay-service {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_bill_pay http://bill-pay-service.relibank-blue.svc.cluster.local:5000;
            proxy_pass $upstream_bill_pay;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /transaction-service {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_transaction http://transaction-service.relibank-blue.svc.cluster.local:5001;
            proxy_pass $upstream_transaction;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /accounts-service {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_accounts http://accounts-service.relibank-blue.svc.cluster.local:5002;
            proxy_pass $upstream_accounts;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /auth-service {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_auth http://auth-service.relibank-blue.svc.cluster.local:5002;
            proxy_pass $upstream_auth;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /support-service {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_support http://support-service.relibank-blue.svc.cluster.local:5003;
            proxy_pass $upstream_support;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /risk-assessment-service {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_risk http://risk-assessment-service.relibank-blue.svc.cluster.local:5001;
            proxy_pass $upstream_risk;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /scenario-runner {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_scenario http://scenario-runner-service.relibank-blue.svc.cluster.local:8000;
            proxy_pass $upstream_scenario;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            if ($http_user_agent = "kube-probe") {
                return 200 "OK";
            }
            set $upstream_frontend http://frontend-service.relibank-blue.svc.cluster.local:3000;
            proxy_pass $upstream_frontend;
            proxy_set_header Host frontend-service.relibank-blue.svc.cluster.local;
            proxy_set_header X-Real-IP "";
            proxy_set_header X-Forwarded-For "";
            proxy_set_header X-Forwarded-Proto "";
        }
    }
    EOF
  }
}

resource "kubernetes_deployment_v1" "blue_proxy" {
  metadata {
    name      = "blue-proxy"
    namespace = "default"
  }

  spec {
    replicas = 1
    selector {
      match_labels = { app = "blue-proxy" }
    }
    template {
      metadata {
        labels = { app = "blue-proxy" }
      }
      spec {
        container {
          name  = "nginx"
          image = "nginx:alpine"
          port {
            container_port = 80
          }
          volume_mount {
            name       = "config"
            mount_path = "/etc/nginx/conf.d"
          }
        }
        volume {
          name = "config"
          config_map {
            name = kubernetes_config_map_v1.blue_proxy_config.metadata[0].name
          }
        }
      }
    }
  }

  depends_on = [kubernetes_config_map_v1.blue_proxy_config]
}

resource "kubernetes_service_v1" "blue_proxy_service" {
  metadata {
    name      = "blue-service"
    namespace = "default"
  }

  spec {
    selector = {
      app = kubernetes_deployment_v1.blue_proxy.spec[0].selector[0].match_labels.app
    }
    port {
      port = 80
    }
  }

  depends_on = [kubernetes_deployment_v1.blue_proxy]
}

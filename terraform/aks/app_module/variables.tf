variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod)"
  type        = string
}

variable "target_color" {
  description = "Deployment color (blue or green)"
  type        = string
  validation {
    condition     = contains(["blue", "green"], var.target_color)
    error_message = "target_color must be 'blue' or 'green'."
  }
}

variable "aks_cluster_name" {
  description = "AKS cluster name"
  type        = string
}

variable "aks_resource_group" {
  description = "Azure resource group for AKS cluster"
  type        = string
}

variable "acr_server" {
  description = "Azure Container Registry server URL"
  type        = string
  default     = "relibank.azurecr.io"
}

variable "mssql_sa_password" {
  description = "MSSQL SA password"
  type        = string
  sensitive   = true
}

variable "mssql_sa_user" {
  description = "MSSQL SA username"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  sensitive   = true
}

variable "locust_host" {
  description = "Locust host URL for scenario runner"
  type        = string
  default     = "http://relibank.local"
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint for support-service. Empty string is OK — support-service will fail on startup but won't block anything else."
  type        = string
  default     = ""
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key for support-service. Empty string is OK — support-service will fail on startup but won't block anything else."
  type        = string
  sensitive   = true
  default     = ""
}

variable "services" {
  description = "Per-service deployment config. Map keys are k8s service names."
  type = map(object({
    image           = string
    container_port  = number
    service_port    = number
    config_map_envs = optional(map(string), {})
    secret_envs     = optional(map(string), {})
    extra_envs      = optional(map(string), {})
    cpu_request     = optional(string)
    cpu_limit       = optional(string)
    memory_request  = optional(string)
    memory_limit    = optional(string)
    replicas        = optional(number, 1)
  }))
  default = {
    "frontend-service" = {
      image          = "frontend-service"
      container_port = 3000
      service_port   = 3000
      cpu_request    = "1000m"
      cpu_limit      = "2000m"
      memory_request = "1Gi"
      memory_limit   = "2Gi"
    }

    "accounts-service" = {
      image          = "accounts-service"
      container_port = 5000
      service_port   = 5002
      config_map_envs = {
        DB_HOST                 = "POSTGRES_SERVER_NAME"
        DB_NAME                 = "POSTGRES_DATABASE_NAME"
        TRANSACTION_SERVICE_URL = "TRANSACTION_SERVICE_URL"
      }
      secret_envs = {
        DB_PASSWORD = "POSTGRES_PASSWORD"
        DB_USER     = "POSTGRES_USER"
      }
    }

    "auth-service" = {
      image          = "auth-service"
      container_port = 5002
      service_port   = 5002
      config_map_envs = {
        DB_HOST = "POSTGRES_SERVER_NAME"
        DB_NAME = "POSTGRES_DATABASE_NAME"
      }
      secret_envs = {
        DB_PASSWORD = "POSTGRES_PASSWORD"
        DB_USER     = "POSTGRES_USER"
      }
    }

    "transaction-service" = {
      image          = "transaction-service"
      container_port = 5000
      service_port   = 5001
      config_map_envs = {
        DB_DATABASE  = "MSSQL_DATABASE_NAME"
        DB_SERVER    = "MSSQL_SERVER_NAME"
        KAFKA_BROKER = "KAFKA_BROKER"
      }
      secret_envs = {
        DB_PASSWORD = "MSSQL_SA_PASSWORD"
        DB_USERNAME = "MSSQL_SA_USER"
      }
    }

    "bill-pay-service" = {
      image          = "bill-pay-service"
      container_port = 5000
      service_port   = 5000
      config_map_envs = {
        KAFKA_BROKER            = "KAFKA_BROKER"
        TRANSACTION_SERVICE_URL = "TRANSACTION_SERVICE_URL"
        SCENARIO_SERVICE_URL    = "SCENARIO_RUNNER_SERVICE_URL"
        ACCOUNTS_SERVICE_URL    = "ACCOUNTS_SERVICE_URL"
      }
    }

    "support-service" = {
      image          = "support-service"
      container_port = 5003
      service_port   = 5003
      config_map_envs = {
        KAFKA_BROKER          = "KAFKA_BROKER"
        AZURE_OPENAI_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
      }
      secret_envs = {
        AZURE_OPENAI_API_KEY = "AZURE_OPENAI_API_KEY"
      }
    }

    "risk-assessment-service" = {
      image          = "risk-assessment-service"
      container_port = 5001
      service_port   = 5001
      config_map_envs = {
        KAFKA_BROKER = "KAFKA_BROKER"
      }
    }

    "notifications-service" = {
      image          = "notifications-service"
      container_port = 5000
      service_port   = 5000
      config_map_envs = {
        KAFKA_BROKER = "KAFKA_BROKER"
      }
    }

    "scheduler-service" = {
      image          = "scheduler-service"
      container_port = 5000
      service_port   = 5004
      config_map_envs = {
        KAFKA_BROKER = "KAFKA_BROKER"
        DB_SERVER    = "MSSQL_SERVER_NAME"
        DB_DATABASE  = "MSSQL_DATABASE_NAME"
      }
      secret_envs = {
        DB_USERNAME = "MSSQL_SA_USER"
        DB_PASSWORD = "MSSQL_SA_PASSWORD"
      }
    }

    "scenario-runner-service" = {
      image          = "scenario-runner"
      container_port = 8000
      service_port   = 8000
      config_map_envs = {
        KAFKA_BROKER = "KAFKA_BROKER"
        DB_SERVER    = "MSSQL_SERVER_NAME"
        DB_DATABASE  = "MSSQL_DATABASE_NAME"
      }
      secret_envs = {
        DB_USERNAME = "MSSQL_SA_USER"
        DB_PASSWORD = "MSSQL_SA_PASSWORD"
      }
    }
  }
}

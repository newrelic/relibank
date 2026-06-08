variable "demo_environment" {
  description = "Environment name (sandbox, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for the AOAI account"
  type        = string
}

variable "aks_resource_group" {
  description = "Resource group that hosts the env's AOAI account (same RG as the AKS cluster)"
  type        = string
}

variable "model_deployment_name" {
  description = "Name of the model deployment that backs the assistants. Must match each assistant's `model` field."
  type        = string
  default     = "gpt-4o"
}

variable "model_name" {
  description = "Underlying Azure OpenAI model name (e.g. gpt-4o)"
  type        = string
  default     = "gpt-4o"
}

variable "model_version" {
  description = "Azure OpenAI model version"
  type        = string
  default     = "2024-11-20"
}

variable "model_capacity" {
  description = "Model deployment capacity in thousands of TPM (Standard SKU)"
  type        = number
  default     = 50
}

variable "assistant_b_delay_seconds" {
  description = "Demo knob — artificial delay before Assistant B (specialist) responds. Set to 8 to demo the bottleneck."
  type        = number
  default     = 0
}

variable "assistants" {
  description = <<-EOT
    Map of assistants to provision via the AOAI Assistants API. Keys are slugs
    (e.g. coordinator, specialist) referenced by the consuming app. Each entry
    must have:
      name         (string)  — display name
      instructions (string)  — system prompt
      model        (string)  — must match a cognitive_deployment name on the AOAI account
      temperature  (number)  — optional, default 1
      top_p        (number)  — optional, default 1
      tools        (list)    — optional, default [], shape per AOAI API (e.g. {type=function, function={...}})
      metadata     (map)     — optional, default {}, ≤16 keys
    Type is `any` because nested tool schemas vary per assistant.
  EOT
  type = any

  default = {
    coordinator = {
      name         = "Relibank Coordinator Agent"
      instructions = <<-EOT
        You are a coordinator agent for Relibank banking services.
        You help customers with general banking inquiries, account information, and transaction queries.

        When you need detailed financial analysis, spending pattern analysis, or complex financial insights,
        call the invoke_specialist_agent function to get help from a financial specialist.

        Be friendly, professional, and helpful. Always prioritize customer satisfaction.
      EOT
      model        = "gpt-4o"
      tools = [
        {
          type = "function"
          function = {
            name        = "invoke_specialist_agent"
            description = "Invoke the financial specialist agent for detailed financial analysis, spending patterns, investment advice, or complex financial queries"
            parameters = {
              type = "object"
              properties = {
                query = {
                  type        = "string"
                  description = "The detailed analysis request to send to the specialist"
                }
              }
              required = ["query"]
            }
          }
        }
      ]
    }

    specialist = {
      name         = "Relibank Financial Specialist"
      instructions = <<-EOT
        You are a financial analysis specialist for Relibank.
        You provide detailed financial insights, spending pattern analysis, investment recommendations,
        and complex financial calculations.

        Provide thorough, data-driven analysis with actionable recommendations.
        Be precise with numbers and calculations. Explain financial concepts clearly.
      EOT
      model        = "gpt-4o"
      tools        = []
    }
  }
}

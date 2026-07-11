terraform {
  backend "azurerm" {
    resource_group_name = "ReliBank"
    # storage_account_name, container_name, and key are injected at runtime
    # via --backend-config flags in the scaling-demo workflow.
  }
}

terraform {
  backend "azurerm" {
    resource_group_name  = "ReliBank"
    storage_account_name = "relibankstate" # relibankstate.blob.core.windows.net
    container_name       = "tfstate"
    # key is set dynamically via CLI: relibank/{environment}/traffic_management.tfstate
    key = "relibank/default/traffic_management.tfstate"
  }
}

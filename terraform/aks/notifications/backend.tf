terraform {
  backend "azurerm" {
    resource_group_name  = "ReliBank"
    storage_account_name = "relibankstate"
    container_name       = "tfstate"
    # key is set dynamically via CLI: relibank/{environment}/notifications.tfstate
    key = "relibank/default/notifications.tfstate"
  }
}

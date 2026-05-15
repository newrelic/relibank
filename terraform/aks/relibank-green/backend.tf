terraform {
  backend "azurerm" {
    resource_group_name  = "ReliBank"
    storage_account_name = "relibankstate" # relibankstate.blob.core.windows.net
    container_name       = "tfstate"
    # key is set dynamically via CLI: relibank/{environment}/green.tfstate
    key = "relibank/default/green.tfstate"
  }
}

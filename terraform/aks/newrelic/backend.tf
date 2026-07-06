terraform {
  backend "azurerm" {
    resource_group_name  = "ReliBank"
    storage_account_name = "relibankstate"
    container_name       = "tfstate"
    # key is set dynamically via CLI: relibank/{environment}/newrelic.tfstate
    key = "relibank/default/newrelic.tfstate"
  }
}

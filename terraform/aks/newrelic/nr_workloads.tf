# workloads for teams by default; should be expanded later
###
# newrelic_workload.relibank_aide_workload.guid
# newrelic_workload.relibank_core_banking_workload.guid
# newrelic_workload.relibank_pat_workload.guid
# newrelic_workload.relibank_platform_workload.guid
# newrelic_workload.accounts_service_get_accounts_int_workload.guid
# newrelic_workload.auth_service_login_int_workload.guid
# newrelic_workload.support_service_assess_payment_risk_int_workload.guid
# newrelic_workload.support_service_chat_with_model_int_workload.guid
###

### STANDARD WORKLOADS ###
# AI & Digital Experiences team
resource "newrelic_workload" "relibank_aide_workload" {
  name       = "ReliBank - AI & Digital Experience Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - AI & Digital Experience'"
  }

  scope_account_ids = [var.new_relic_account_id]
}
# Core Banking team
resource "newrelic_workload" "relibank_core_banking_workload" {
  name       = "ReliBank - Core Banking Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - Core Banking'"
  }

  scope_account_ids = [var.new_relic_account_id]
}
# Payments & Transactions team
resource "newrelic_workload" "relibank_pat_workload" {
  name       = "ReliBank - Payments & Transaction Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - Payments & Transactions'"
  }

  scope_account_ids = [var.new_relic_account_id]
}
# Platform team
resource "newrelic_workload" "relibank_platform_workload" {
  name       = "ReliBank - Platform Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - Platform'"
  }

  scope_account_ids = [var.new_relic_account_id]
}

### INTELLIGENT WORKLOADS ###
# accounts_service:get_accounts
resource "newrelic_workload" "accounts_service_get_accounts_int_workload" {
  name       = "accounts_service:get_accounts"
  account_id = var.new_relic_account_id

  dynamic_flows {
    entity_guid      = "${data.newrelic_entity.accounts_service.guid}"
    transaction_name = "WebTransaction/Function/accounts_service:get_accounts"
  }

  scope_account_ids = [var.new_relic_account_id]
}
# auth_service:login
resource "newrelic_workload" "auth_service_login_int_workload" {
  name       = "auth_service:login"
  account_id = var.new_relic_account_id

  dynamic_flows {
    entity_guid      = "${data.newrelic_entity.auth_service.guid}"
    transaction_name = "WebTransaction/Function/auth_service:login"
  }

  scope_account_ids = [var.new_relic_account_id]
}
# support_service:assess_payment_risk
resource "newrelic_workload" "support_service_assess_payment_risk_int_workload" {
  name       = "support_service:assess_payment_risk"
  account_id = var.new_relic_account_id

  dynamic_flows {
    entity_guid      = "${data.newrelic_entity.support_service.guid}"
    transaction_name = "WebTransaction/Function/support_service:assess_payment_risk"
  }

  scope_account_ids = [var.new_relic_account_id]
}
# support_service:chat_with_model
resource "newrelic_workload" "support_service_chat_with_model_int_workload" {
  name       = "support_service:chat_with_model"
  account_id = var.new_relic_account_id

  dynamic_flows {
    entity_guid      = "${data.newrelic_entity.support_service.guid}"
    transaction_name = "WebTransaction/Function/support_service:chat_with_model"
  }

  scope_account_ids = [var.new_relic_account_id]
}

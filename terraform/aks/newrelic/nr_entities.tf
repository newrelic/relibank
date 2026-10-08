# TMM: Add data sources for the other 9 APM services (accounts, auth, transaction, bill-pay,
# notifications, scheduler, risk-assessment, scenario-runner, frontend) and the Browser app.
# APM entities resolve at plan time by name `${var.app_name} - <Service>` — requires the app
# tier to be deployed and services reporting before apply.

data "newrelic_entity" "support_service" {
  name       = "${var.app_name} - Support Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}

data "newrelic_entity" "kafka_bill_payments_topic" {
  name       = "bill_payments"
  domain     = "INFRA"
  type       = "KAFKATOPIC"
  account_id = var.new_relic_account_id
}

data "newrelic_entity" "kafka_bill_payments_declined_topic" {
  name       = "bill_payments_declined"
  domain     = "INFRA"
  type       = "KAFKATOPIC"
  account_id = var.new_relic_account_id
}

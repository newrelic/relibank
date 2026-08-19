# utilizes template files to load JSON
###
# newrelic_one_dashboard_json.relibank_summary.guid
# newrelic_one_dashboard_json.relibank_bill_pay_metrics.guid
###

# ecomm summary dashboard
resource "newrelic_one_dashboard_json" "relibank_summary" {
  json = templatefile("dashboards/relibank_summary.json.tftpl", {
    account_id                     = var.new_relic_account_id,
    cluster_name                   = "relibank-${var.demo_environment}"
    accounts_service               = data.newrelic_entity.accounts_service.guid,
    bill_pay_service               = data.newrelic_entity.bill_pay_service.guid,
    transaction_service            = data.newrelic_entity.transaction_service.guid,
    transaction_service_success_sl = newrelic_service_level.transaction_service_success_sl.sli_guid
    customer_portal                = data.newrelic_entity.customer_portal_browser.guid
  })
  depends_on = [
    data.newrelic_entity.accounts_service,
    data.newrelic_entity.bill_pay_service,
    data.newrelic_entity.transaction_service,
    newrelic_service_level.transaction_service_success_sl,
    data.newrelic_entity.customer_portal_browser
  ]
}

# bill pay metrics dashboard
resource "newrelic_one_dashboard_json" "relibank_bill_pay_metrics" {
  json = templatefile("dashboards/relibank_bill_pay_metrics.json.tftpl", {
    account_id       = var.new_relic_account_id,
    bill_pay_service = data.newrelic_entity.bill_pay_service.guid
  })
  depends_on = [
    data.newrelic_entity.bill_pay_service
  ]
}

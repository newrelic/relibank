# TMM: Add new `.json.tftpl` files under `./dashboards/` and one matching
# `newrelic_one_dashboard_json` resource per dashboard.

resource "newrelic_one_dashboard_json" "placeholder" {
  json = templatefile("${path.module}/dashboards/placeholder.json.tftpl", {
    app_name             = var.app_name
    account_id           = tonumber(var.new_relic_account_id)
    support_service_guid = data.newrelic_entity.support_service.guid
  })
}

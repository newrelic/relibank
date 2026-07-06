# TMM: Replace this placeholder workload with real ones grouped by team / ownership / function.
# For multi-team, demogorgon's nr_workloads.tf iterates with `count` over a `locals.nr_team_list`.

resource "newrelic_workload" "placeholder" {
  name       = "${var.app_name} - Placeholder Workload"
  account_id = var.new_relic_account_id

  entity_guids = [
    data.newrelic_entity.support_service.guid,
  ]
}

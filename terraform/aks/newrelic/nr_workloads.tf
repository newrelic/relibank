# workloads for teams by default; should be expanded later
###
# newrelic_workload.relibank_aide_workload.guid
# newrelic_workload.relibank_core_banking_workload.guid
# newrelic_workload.relibank_pat_workload.guid
# newrelic_workload.relibank_platform_workload.guid
###

resource "newrelic_workload" "relibank_aide_workload" {
  name       = "ReliBank - AI & Digital Experience Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - AI & Digital Experience'"
  }
}

resource "newrelic_workload" "relibank_core_banking_workload" {
  name       = "ReliBank - Core Banking Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - Core Banking'"
  }
}

resource "newrelic_workload" "relibank_pat_workload" {
  name       = "ReliBank - Payments & Transaction Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - Payments & Transactions'"
  }
}

resource "newrelic_workload" "relibank_platform_workload" {
  name       = "ReliBank - Platform Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliBank - Platform'"
  }
}

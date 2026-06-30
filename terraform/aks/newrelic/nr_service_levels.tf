# TMM: Replace this placeholder SLI with real ones. Pattern is latency + success per service;
# demogorgon's nr_service_levels.tf is the reference for the full set.

resource "newrelic_service_level" "placeholder_support_service_latency" {
  guid        = data.newrelic_entity.support_service.guid
  name        = "${data.newrelic_entity.support_service.name} - Latency"
  description = "Proportion of support-service requests served faster than 400ms."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.support_service.guid}' AND (transactionType = 'Web')"
    }

    good_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.support_service.guid}' AND (transactionType = 'Web') AND duration < 0.4"
    }
  }

  objective {
    target = 95

    time_window {
      rolling {
        count = 7
        unit  = "DAY"
      }
    }
  }
}

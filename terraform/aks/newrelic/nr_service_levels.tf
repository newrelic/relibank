# service levels across relibank
# focused on success only, latency may be added later but right now it's mainly red always
###
# newrelic_service_level.accounts_service_success_sl.sli_guid
# newrelic_service_level.auth_service_success_sl.sli_guid
# newrelic_service_level.bill_pay_service_success_sl.sli_guid
# newrelic_service_level.event_scheduler_service_success_sl.sli_guid
# newrelic_service_level.notifications_service_success_sl.sli_guid
# newrelic_service_level.support_service_success_sl.sli_guid
# newrelic_service_level.transaction_service_success_sl.sli_guid
# newrelic_service_level.customer_portal_browser_success_sl.sli_guid
###

# apm accounts service success service level
resource "newrelic_service_level" "accounts_service_success_sl" {
  guid        = data.newrelic_entity.accounts_service.guid
  name        = "${data.newrelic_entity.accounts_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.accounts_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.accounts_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.accounts_service]
}
# apm auth service success service level
resource "newrelic_service_level" "auth_service_success_sl" {
  guid        = data.newrelic_entity.auth_service.guid
  name        = "${data.newrelic_entity.auth_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.auth_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.auth_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.auth_service]
}
# apm bill pay service success service level
resource "newrelic_service_level" "bill_pay_service_success_sl" {
  guid        = data.newrelic_entity.bill_pay_service.guid
  name        = "${data.newrelic_entity.bill_pay_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.bill_pay_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.bill_pay_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.bill_pay_service]
}
# apm event scheduler service success service level
resource "newrelic_service_level" "event_scheduler_service_success_sl" {
  guid        = data.newrelic_entity.event_scheduler_service.guid
  name        = "${data.newrelic_entity.event_scheduler_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.event_scheduler_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.event_scheduler_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.event_scheduler_service]
}
# apm notifications service success service level
resource "newrelic_service_level" "notifications_service_success_sl" {
  guid        = data.newrelic_entity.notifications_service.guid
  name        = "${data.newrelic_entity.notifications_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.notifications_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.notifications_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.notifications_service]
}
# apm support service success service level
resource "newrelic_service_level" "support_service_success_sl" {
  guid        = data.newrelic_entity.support_service.guid
  name        = "${data.newrelic_entity.support_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.support_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.support_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.support_service]
}
# apm transaction service success service level
resource "newrelic_service_level" "transaction_service_success_sl" {
  guid        = data.newrelic_entity.transaction_service.guid
  name        = "${data.newrelic_entity.transaction_service.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.transaction_service.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.transaction_service.guid}' AND error.expected != true"
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

  depends_on = [data.newrelic_entity.transaction_service]
}

# browser customer portal success service level
resource "newrelic_service_level" "customer_portal_browser_success_sl" {
  guid        = data.newrelic_entity.customer_portal_browser.guid
  name        = "${data.newrelic_entity.customer_portal_browser.name} Browser - Success"
  description = "Proportion of page views that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "PageView"
      where = "entityGuid = '${data.newrelic_entity.customer_portal_browser.guid}'"
    }

    bad_events {
      from  = "JavaScriptError"
      where = "entityGuid = '${data.newrelic_entity.customer_portal_browser.guid}' AND firstErrorInSession IS true"
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

  depends_on = [data.newrelic_entity.customer_portal_browser]
}

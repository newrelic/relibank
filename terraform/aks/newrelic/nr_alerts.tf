# TMM: Replace these placeholder alert policy / condition / destination / channel / workflow
# with real definitions. The chain below is end-to-end wired so apply succeeds.

resource "newrelic_alert_policy" "placeholder" {
  name                = "${var.app_name} - Placeholder Policy"
  incident_preference = "PER_CONDITION"
  account_id          = var.new_relic_account_id
}

resource "newrelic_nrql_alert_condition" "placeholder_support_service_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.placeholder.id
  type                         = "static"
  name                         = "${var.app_name} - Placeholder Support Service Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800

  nrql {
    query           = "FROM Metric SELECT (count(apm.service.error.count) / count(apm.service.transaction.duration)) * 100 WHERE entityGuid = '${data.newrelic_entity.support_service.guid}'"
    data_account_id = var.new_relic_account_id
  }

  critical {
    operator              = "above"
    threshold             = 5
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
}

resource "newrelic_notification_destination" "placeholder_email" {
  account_id = var.new_relic_account_id
  name       = "${var.app_name} - Placeholder Email Destination"
  type       = "EMAIL"

  property {
    key   = "email"
    value = "relibank-placeholder@example.com"
  }
}

resource "newrelic_notification_channel" "placeholder_email_template" {
  account_id     = var.new_relic_account_id
  name           = "${var.app_name} - Placeholder Email Template"
  type           = "EMAIL"
  destination_id = newrelic_notification_destination.placeholder_email.id
  product        = "IINT"

  property {
    key   = "subject"
    value = "{{ issueTitle }}"
  }
}

resource "newrelic_workflow" "placeholder_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "${var.app_name} - Placeholder Workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values    = ["${newrelic_alert_policy.placeholder.id}"]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.placeholder_email_template.id
    notification_triggers   = ["ACTIVATED", "ACKNOWLEDGED", "CLOSED"]
    update_original_message = true
  }
}

# alert policies, destinations, channels, and workflows
###
# newrelic_notification_channel.autopilot_channel.id
# newrelic_notification_channel.staging_slack_relibank_channel.id
# newrelic_workflow.autopilot_and_slack_workflow.id

# newrelic_alert_policy.aide_policy.id
# newrelic_nrql_alert_condition.aide_chat_with_model.entity_guid
# newrelic_nrql_alert_condition.aide_high_response_time.entity_guid
# newrelic_nrql_alert_condition.aide_high_error_rate.entity_guid
# newrelic_nrql_alert_condition.aide_low_throughput.entity_guid
# newrelic_nrql_alert_condition.aide_high_inp.entity_guid
# newrelic_nrql_alert_condition.high_lcp.entity_guid
# newrelic_nrql_alert_condition.high_js_error_rate.entity_guid
# newrelic_nrql_alert_condition.high_page_load_time.entity_guid
# newrelic_nrql_alert_condition.aide_ai_agent_health.entity_guid
# newrelic_nrql_alert_condition.aide_ai_tool_health.entity_guid
# newrelic_nrql_alert_condition.aide_service_level_health.entity_guid
# newrelic_nrql_alert_condition.aide_synthetic_failing.entity_guid

# newrelic_alert_policy.core_banking_policy.id
# newrelic_nrql_alert_condition.core_banking_high_response_time.entity_guid
# newrelic_nrql_alert_condition.core_banking_high_error_rate.entity_guid
# newrelic_nrql_alert_condition.core_banking_low_throughput.entity_guid
# newrelic_nrql_alert_condition.core_banking_service_level_health.entity_guid

# newrelic_alert_policy.pat_policy.id
# newrelic_nrql_alert_condition.pat_high_response_time.entity_guid
# newrelic_nrql_alert_condition.pat_high_error_rate.entity_guid
# newrelic_nrql_alert_condition.pat_low_throughput.entity_guid
# newrelic_nrql_alert_condition.pat_service_level_health.entity_guid

# newrelic_alert_policy.platform_policy.id
# newrelic_nrql_alert_condition.platform_high_response_time.entity_guid
# newrelic_nrql_alert_condition.platform_high_error_rate.entity_guid
# newrelic_nrql_alert_condition.platform_low_throughput.entity_guid
# newrelic_nrql_alert_condition.platform_service_level_health.entity_guid
# newrelic_nrql_alert_condition.platform_k8s_cluster_health.entity_guid
# newrelic_nrql_alert_condition.platform_k8s_deployment_health.entity_guid
# newrelic_nrql_alert_condition.platform_kafka_broker_health.entity_guid
# newrelic_nrql_alert_condition.platform_kafka_cluster_health.entity_guid
# newrelic_nrql_alert_condition.platform_kafka_topic_health.entity_guid
# newrelic_nrql_alert_condition.platform_database_health.entity_guid

# newrelic_alert_policy.before_autopilot_policy.id
# newrelic_notification_channel.before_autopilot_slack_channel.id
# newrelic_workflow.before_autopilot_workflow.id
# newrelic_nrql_alert_condition.legacy_chat_with_model.entity_guid

# autopilot_plus_wa_policy.id
# newrelic_notification_destination.github_scale_relibank_service_destination.id
# workflow_automation_channel.id
# newrelic_notification_channel.autopilot_plus_wa_channel.id
# newrelic_workflow.autopilot_plus_wa_workflow.id
# newrelic_nrql_alert_condition.wa_bill_pay_errors.entity_guid
###

locals {
  # IDs for global destinations already configured in New Relic
  autopilot_destination_id     = "c38e93bf-c98c-461b-b278-432d97d61cf6"
  staging_slack_destination_id = "4e9f3925-0289-4ca0-a585-523e112daa56"
}

### Global Workflows ###
# Autopilot Notification Channel
resource "newrelic_notification_channel" "autopilot_channel" {
  account_id     = var.new_relic_account_id
  name           = "autopilot_channel"
  type           = "WEBHOOK"
  destination_id = local.autopilot_destination_id
  product        = "IINT"

  property {
    key = "headers"
    value = trimspace(<<-EOT
    {"x-respond-async":"true","x-Account-Id":"{{nrAccountId}}"}
    EOT
    )
  }

  property {
    key   = "payload"
    value = file("${path.module}/alert_channels/autopilot_payload.json")
  }
}
# Staging Slack Notification Channel
resource "newrelic_notification_channel" "staging_slack_relibank_channel" {
  account_id     = var.new_relic_account_id
  name           = "staging_slack_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BQ8HY3ZEZ"
    display_value = "relibank-demo-alerts"
  }
}
# Autopilot Workflow
resource "newrelic_workflow" "autopilot_and_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "autopilot_and_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.aide_policy.id,
        newrelic_alert_policy.core_banking_policy.id,
        newrelic_alert_policy.pat_policy.id,
        newrelic_alert_policy.platform_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.autopilot_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.staging_slack_relibank_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}

### AI & Digital Experience ###
resource "newrelic_alert_policy" "aide_policy" {
  name                = "ReliBank - AI & Digital Experience Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# Support Service - chat_with_model Error Rate
resource "newrelic_nrql_alert_condition" "aide_chat_with_model" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE chat_with_model - High Transaction Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      sum(apm.service.transaction.error.count['count']) / count(apm.service.transaction.duration)
    FACET entity.name AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    AND entity.name = '${var.app_name} - Support Service'
    AND transactionName = 'WebTransaction/Function/support_service:chat_with_model'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 0.95
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
  title_template     = "High Transaction Error Rate | {{ entity_name }}"
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "aide_high_response_time" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High Response Time"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 90000
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Response Time | {{ entity_name }}"
}
# APM Error Rate
resource "newrelic_nrql_alert_condition" "aide_high_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      (count(apm.service.error.count) / count(apm.service.transaction.duration)) * 100
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 91
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Error Rate | {{ entity_name }}"
}
# APM Throughput
resource "newrelic_nrql_alert_condition" "aide_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      count(apm.service.transaction.duration)
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Low Throughput | {{ entity_name }}"
}
# Browser INP
resource "newrelic_nrql_alert_condition" "aide_high_inp" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High INP"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageViewTiming SELECT
      percentile(interactionToNextPaint, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 24000
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High INP | {{ entity_name }}"
}
# Browser LCP
resource "newrelic_nrql_alert_condition" "aide_high_lcp" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High LCP"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageViewTiming SELECT
      percentile(largestContentfulPaint, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 28100
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High LCP | {{ entity_name }}"
}
# Browser JS Error Rate
resource "newrelic_nrql_alert_condition" "high_js_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High JS Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM JavaScriptError SELECT
      rate(count(*), 1 minute)
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 50
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High JS Error Rate | {{ entity_name }}"
}
# Browser Page Load Time
resource "newrelic_nrql_alert_condition" "high_page_load_time" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High Page Load Time"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageView SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 31100
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Page Load Time | {{ entity_name }}"
}
# AI Agent Health
resource "newrelic_nrql_alert_condition" "aide_ai_agent_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - AI Agent Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'APM-AI_AGENT'
    AND tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "AI Agent Health | {{ entity_name }}"
}
# AI Tool Health
resource "newrelic_nrql_alert_condition" "aide_ai_tool_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High AI Tool Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'APM-AI_TOOL'
    AND tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "AI Tool Health | {{ entity_name }}"
}
# Service Level Health
resource "newrelic_nrql_alert_condition" "aide_service_level_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - Service Level Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'EXT-SERVICE_LEVEL'
    AND tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Service Level Health | {{ entity_name }}"
}
# Synthetics Failing
resource "newrelic_nrql_alert_condition" "aide_synthetic_failing" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - Synthetic Check Failing"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM SyntheticCheck SELECT
      percentage(count(*), WHERE result = 'FAILED')
    FACET location, monitorName AS 'entityName'
    WHERE NOT isMuted
    AND tags.team = 'ReliBank - AI & Digital Experience'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 0
    threshold_duration    = 60
    threshold_occurrences = "at_least_once"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Synthetic Check Failing | {{ entity_name }}"
}

### Core Banking ###
resource "newrelic_alert_policy" "core_banking_policy" {
  name                = "ReliBank - Core Banking Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "core_banking_high_response_time" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - High Response Time"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - Core Banking'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 90000
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Response Time | {{ entity_name }}"
}
# APM Error Rate
resource "newrelic_nrql_alert_condition" "core_banking_high_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - High Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      (count(apm.service.error.count) / count(apm.service.transaction.duration)) * 100
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - Core Banking'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 91
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Error Rate | {{ entity_name }}"
}
# APM Throughput
resource "newrelic_nrql_alert_condition" "core_banking_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      count(apm.service.transaction.duration)
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - Core Banking'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Low Throughput | {{ entity_name }}"
}
# Service Level Health
resource "newrelic_nrql_alert_condition" "core_banking_service_level_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - Service Level Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'EXT-SERVICE_LEVEL'
    AND tags.team = 'ReliBank - Core Banking'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Service Level Health | {{ entity_name }}"
}

### Payments & Transactions ###
resource "newrelic_alert_policy" "pat_policy" {
  name                = "ReliBank - Payments & Transactions Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "pat_high_response_time" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - High Response Time"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - Payments & Transactions'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 90000
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Response Time | {{ entity_name }}"
}
# APM Error Rate
resource "newrelic_nrql_alert_condition" "pat_high_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - High Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      (count(apm.service.error.count) / count(apm.service.transaction.duration)) * 100
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - Payments & Transactions'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 91
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Error Rate | {{ entity_name }}"
}
# APM Throughput
resource "newrelic_nrql_alert_condition" "pat_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      count(apm.service.transaction.duration)
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - Payments & Transactions'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Low Throughput | {{ entity_name }}"
}
# Service Level Health
resource "newrelic_nrql_alert_condition" "pat_service_level_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - Service Level Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'EXT-SERVICE_LEVEL'
    AND tags.team = 'ReliBank - Payments & Transactions'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Service Level Health | {{ entity_name }}"
}

### Platform ###
resource "newrelic_alert_policy" "platform_policy" {
  name                = "ReliBank - Platform Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "platform_high_response_time" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - High Response Time"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 90000
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Response Time | {{ entity_name }}"
}
# APM Error Rate
resource "newrelic_nrql_alert_condition" "platform_high_error_rate" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - High Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      (count(apm.service.error.count) / count(apm.service.transaction.duration)) * 100
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 91
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Error Rate | {{ entity_name }}"
}
# APM Throughput
resource "newrelic_nrql_alert_condition" "platform_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      count(apm.service.transaction.duration)
    FACET appName AS 'entityName'
    WHERE appName LIKE '%'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Low Throughput | {{ entity_name }}"
}
# Service Level Health
resource "newrelic_nrql_alert_condition" "platform_service_level_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Service Level Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'EXT-SERVICE_LEVEL'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Service Level Health | {{ entity_name }}"
}
# K8s Cluster Health
resource "newrelic_nrql_alert_condition" "platform_k8s_cluster_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - K8s Cluster Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'INFRA-KUBERNETESCLUSTER'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "K8s Cluster Health | {{ entity_name }}"
}
# K8s Deployment Health
resource "newrelic_nrql_alert_condition" "platform_k8s_deployment_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - K8s Deployment Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'INFRA-KUBERNETES_DEPLOYMENT'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "K8s Deployment Health | {{ entity_name }}"
}
# Kafka Broker Health
resource "newrelic_nrql_alert_condition" "platform_kafka_broker_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Kafka Broker Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'INFRA-KAFKABROKER'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Kafka Broker Health | {{ entity_name }}"
}
# Kafka Cluster Health
resource "newrelic_nrql_alert_condition" "platform_kafka_cluster_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Kafka Cluster Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'INFRA-KAFKACLUSTER'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Kafka Cluster Health | {{ entity_name }}"
}
# Kafka Topic Health
resource "newrelic_nrql_alert_condition" "platform_kafka_topic_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Kafka Topic Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'INFRA-KAFKATOPIC'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Kafka Topic Health | {{ entity_name }}"
}
# Database Health
resource "newrelic_nrql_alert_condition" "platform_database_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Database Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'INFRA-MSSQLINSTANCE'
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Database Health | {{ entity_name }}"
}


### Before Autopilot ###
resource "newrelic_alert_policy" "before_autopilot_policy" {
  name                = "ReliBank - Before Autopilot Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# Staging Slack Notification Channel
resource "newrelic_notification_channel" "before_autopilot_slack_channel" {
  account_id     = var.new_relic_account_id
  name           = "before_autopilot_slack_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BQD441JBC"
    display_value = "relibank-before-autopilot"
  }
}
# Legacy Workflow
resource "newrelic_workflow" "before_autopilot_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "before_autopilot_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.before_autopilot_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.before_autopilot_slack_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}
# Legacy Support Service - chat_with_model Error Rate
resource "newrelic_nrql_alert_condition" "legacy_chat_with_model" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.before_autopilot_policy.id
  type                         = "static"
  name                         = "Legacy chat_with_model - High Transaction Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      sum(apm.service.transaction.error.count['count']) / count(apm.service.transaction.duration)
    FACET entity.name AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    AND entity.name = '${var.app_name} - Support Service'
    AND transactionName = 'WebTransaction/Function/support_service:chat_with_model'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 0.95
    threshold_duration    = 300
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
  title_template     = "High Transaction Error Rate | {{ entity_name }}"
}

### Autopilot + Workflow Automation ###
# Specific policy used to invoke Autopilot + Workflow Automation
resource "newrelic_alert_policy" "autopilot_plus_wa_policy" {
  name                = "ReliBank - Autopilot + Workflow Automation Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# Workflow Automation Destination
resource "newrelic_notification_destination" "github_scale_relibank_service_destination" {
  account_id = var.new_relic_account_id
  name       = "github_scale_relibank_service_destination"
  type       = "WORKFLOW_AUTOMATION"

  auth_custom_header {
    key   = "Api-Key"
    value = var.new_relic_user_api_key
  }

  property {
    key   = ""
    value = ""
  }
}
# Autopilot Notification Channel (dedicated — channels can only be attached to one
# workflow, so this can't reuse the global `autopilot_channel` from autopilot_and_slack_workflow)
resource "newrelic_notification_channel" "autopilot_plus_wa_channel" {
  account_id     = var.new_relic_account_id
  name           = "autopilot_plus_wa_channel"
  type           = "WEBHOOK"
  destination_id = local.autopilot_destination_id
  product        = "IINT"

  property {
    key = "headers"
    value = trimspace(<<-EOT
    {"x-respond-async":"true","x-Account-Id":"{{nrAccountId}}"}
    EOT
    )
  }

  property {
    key   = "payload"
    value = file("${path.module}/alert_channels/autopilot_payload.json")
  }
}
# Channel for Destination
resource "newrelic_notification_channel" "workflow_automation_channel" {
  account_id     = var.new_relic_account_id
  name           = "github_scale_relibank_service Channel"
  type           = "WORKFLOW_AUTOMATION"
  destination_id = newrelic_notification_destination.github_scale_relibank_service_destination.id
  product        = "IINT"

  property {
    key           = "workflowAutomation"
    value         = "github_scale_relibank_service"
    label         = "Workflow Automation Name"
    display_value = "github_scale_relibank_service"
  }

  property {
    key           = "workflowAutomationVersion"
    value         = tostring(newrelic_workflow_automation.github_scale_relibank_service.version)
    label         = "Select Version"
    display_value = tostring(newrelic_workflow_automation.github_scale_relibank_service.version)
  }

  property {
    key   = "issueId"
    value = "{{ issueId }}"
    label = "IssueId"
  }

  property {
    key   = "accountId"
    value = var.new_relic_account_id
    label = "AccountId"
  }
}
# Workflow that invokes Autopilot + Workflow Automation
resource "newrelic_workflow" "autopilot_plus_wa_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "Autopilot + Workflow Automation Workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values    = ["${newrelic_alert_policy.autopilot_plus_wa_policy.id}"]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.autopilot_plus_wa_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.workflow_automation_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING", "OTHER_UPDATES", "PRIORITY_CHANGED"]
    update_original_message = true
  }
}
# NRQL Alert
resource "newrelic_nrql_alert_condition" "wa_bill_pay_errors" {
  account_id = var.new_relic_account_id
  policy_id  = newrelic_alert_policy.autopilot_plus_wa_policy.id
  type       = "static"
  name       = "WA: ReliBank Bill Pay - 403 Error"
  description = trimspace(<<-EOT
  A high percentage of Bill Payments are being rejected.
  EOT
  )
  enabled                      = true
  violation_time_limit_seconds = 10800

  nrql {
    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentage(count(*), WHERE response.status = '403') AS sec_decline_rate
    WHERE appName = '${data.newrelic_entity.bill_pay_service.name}' 
    AND response.status IN ('200', '402','409', '503', '403')
    EOT
    )
    data_account_id = var.new_relic_account_id
  }

  critical {
    operator              = "above"
    threshold             = 15
    threshold_duration    = 180
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
  title_template     = "WARNING - High Bill Payment Rejection Rate"
}

# alert policies, destinations, channels, and workflows
# "health" alerts are in place to remove 'unknown' entity status
###
# newrelic_notification_channel.aide_autopilot_channel.id
# newrelic_notification_channel.aide_staging_slack_channel.id
# newrelic_workflow.aide_autopilot_and_slack_workflow.id
# newrelic_alert_policy.aide_policy.id
# newrelic_nrql_alert_condition.aide_assess_payment_risk.entity_guid
# newrelic_nrql_alert_condition.aide_high_response_time_health.entity_guid
# newrelic_nrql_alert_condition.aide_high_error_rate_health.entity_guid
# newrelic_nrql_alert_condition.aide_low_throughput_health.entity_guid
# newrelic_nrql_alert_condition.aide_high_inp_health.entity_guid
# newrelic_nrql_alert_condition.aide_high_lcp_health.entity_guid
# newrelic_nrql_alert_condition.aide_high_js_error_rate_health.entity_guid
# newrelic_nrql_alert_condition.aide_high_page_load_time_health.entity_guid
# newrelic_nrql_alert_condition.aide_high_mfe_load_time_health.entity_guid
# newrelic_nrql_alert_condition.aide_ai_agent_health.entity_guid
# newrelic_nrql_alert_condition.aide_ai_tool_health.entity_guid
# newrelic_nrql_alert_condition.aide_service_level_health.entity_guid
# newrelic_nrql_alert_condition.aide_synthetic_failing_health.entity_guid

# newrelic_notification_channel.core_autopilot_channel.id
# newrelic_notification_channel.core_staging_slack_channel.id
# newrelic_workflow.core_autopilot_and_slack_workflow.id
# newrelic_alert_policy.core_banking_policy.id
# newrelic_nrql_alert_condition.core_banking_high_response_time_health.entity_guid
# newrelic_nrql_alert_condition.core_banking_high_error_rate_health.entity_guid
# newrelic_nrql_alert_condition.core_banking_low_throughput_health.entity_guid
# newrelic_nrql_alert_condition.core_banking_service_level_health.entity_guid

# newrelic_notification_channel.pat_autopilot_channel.id
# newrelic_notification_channel.pat_staging_slack_channel.id
# newrelic_workflow.pat_autopilot_and_slack_workflow.id
# newrelic_alert_policy.pat_policy.id
# newrelic_nrql_alert_condition.pat_transaction_service_high_response_time.entity_guid
# newrelic_nrql_alert_condition.pat_high_response_time_health.entity_guid
# newrelic_nrql_alert_condition.pat_high_error_rate_health.entity_guid
# newrelic_nrql_alert_condition.pat_low_throughput_health.entity_guid
# newrelic_nrql_alert_condition.pat_service_level_health.entity_guid

# newrelic_notification_channel.platform_autopilot_channel.id
# newrelic_notification_channel.platform_staging_slack_channel.id
# newrelic_workflow.platform_autopilot_and_slack_workflow.id
# newrelic_alert_policy.platform_policy.id
# newrelic_nrql_alert_condition.platform_high_response_time_health.entity_guid
# newrelic_nrql_alert_condition.platform_high_error_rate_health.entity_guid
# newrelic_nrql_alert_condition.platform_low_throughput_health.entity_guid
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
# newrelic_nrql_alert_condition.before_autopilot_assess_payment_risk.entity_guid

# newrelic_alert_policy.apwa_policy.id
# newrelic_notification_destination.apwa_destination.id
# newrelic_notification_channel.apwa_autopilot_channel.id
# newrelic_notification_channel.apwa_workflow_channel.id
# newrelic_workflow.apwa_workflow.id
# newrelic_nrql_alert_condition.apwa_bill_pay_errors.entity_guid

# newrelic_notification_channel.staging_slack_relibank_mobile_channel.id
# newrelic_workflow.mobile_slack_workflow.id
# newrelic_alert_policy.aide_mobile_policy.id
# newrelic_nrql_alert_condition.aide_android_excess_transfer_attempts.entity_guid
###

//TODO - move these to repo vars
locals {
  # IDs for global destinations already configured in New Relic
  autopilot_destination_id     = "c38e93bf-c98c-461b-b278-432d97d61cf6"
  staging_slack_destination_id = "4e9f3925-0289-4ca0-a585-523e112daa56"
}

### AI & Digital Experience ###

# AIDE Autopilot Channel
resource "newrelic_notification_channel" "aide_autopilot_channel" {
  account_id     = var.new_relic_account_id
  name           = "aide_autopilot_channel"
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
# AIDE Staging Slack Channel
resource "newrelic_notification_channel" "aide_staging_slack_channel" {
  account_id     = var.new_relic_account_id
  name           = "aide_staging_slack_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BQ6VAE9GB"
    display_value = "help-relibank-ai-and-exp"
  }
}
# AIDE Workflow
resource "newrelic_workflow" "aide_autopilot_and_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "aide_autopilot_and_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.aide_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.aide_autopilot_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.aide_staging_slack_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}
# AIDE Policy
resource "newrelic_alert_policy" "aide_policy" {
  name                = "ReliBank - AI & Digital Experience Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# Support Service - assess_payment_risk Error Rate
resource "newrelic_nrql_alert_condition" "aide_assess_payment_risk" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE assess_payment_risk - High Transaction Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      latest(apm.service.transaction.error.count['count'])
    FACET entity.name AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    AND transactionName = 'WebTransaction/Function/support_service:assess_payment_risk'
    EOT
    )

    data_account_id = var.new_relic_account_id

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
  title_template     = "Transaction Errors on 'assess_payment_risk'"
}

## HEALTH ALERTS USED TO CONTROL ENTITY STATUS ##

# APM Response Time
resource "newrelic_nrql_alert_condition" "aide_high_response_time_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High Response Time Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    AND entityGuid != '${data.newrelic_entity.transaction_service.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "above"
    threshold             = 20000
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
resource "newrelic_nrql_alert_condition" "aide_high_error_rate_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High Error Rate Health"
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

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "aide_low_throughput_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - Low Throughput Health"
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

    data_account_id = var.new_relic_account_id

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
### Browser alerts filter directly on the GUID as none of their
### telemetry decorates itself with the entity tags
# Browser INP
resource "newrelic_nrql_alert_condition" "aide_high_inp_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High INP Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageViewTiming SELECT
      percentile(interactionToNextPaint, 99) * 1000
    FACET appName AS 'entityName'
    WHERE entityGuid = '${data.newrelic_entity.customer_portal_browser.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "aide_high_lcp_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High LCP Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageViewTiming SELECT
      percentile(largestContentfulPaint, 99) * 1000
    FACET appName AS 'entityName'
    WHERE entityGuid = '${data.newrelic_entity.customer_portal_browser.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "aide_high_js_error_rate_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High JS Error Rate Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM JavaScriptError SELECT
      rate(count(*), 1 minute)
    FACET appName AS 'entityName'
    WHERE entityGuid = '${data.newrelic_entity.customer_portal_browser.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "aide_high_page_load_time_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High Page Load Time Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageView SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE entityGuid = '${data.newrelic_entity.customer_portal_browser.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

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
# Micro-Frontend Time to Load
//TODO - Once MFE is GA we should be creating them with TF and then filtering on tags here
resource "newrelic_nrql_alert_condition" "aide_high_mfe_load_time_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - High MFE Load Time Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM MicroFrontEndTiming SELECT
      average(timeToLoad)
    FACET entity.name
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "above"
    threshold             = 5000
    threshold_duration    = 600
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High MFE Load Time | {{ entity_name }}"
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

    data_account_id = var.new_relic_account_id

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
  name                         = "AIDE - AI Tool Health"
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

    data_account_id = var.new_relic_account_id

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
    FROM ServiceLevelSnapshot SELECT
      count(*)
    FACET entity.name, entity.guid
    WHERE entity.guid IN (${join(",", [for g in local.relibank_aide_sli_guids : "'${g}'"])})
    EOT
    )

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "aide_synthetic_failing_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_policy.id
  type                         = "static"
  name                         = "AIDE - Synthetic Check Health"
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

    data_account_id = var.new_relic_account_id

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

# CORE Autopilot Channel
resource "newrelic_notification_channel" "core_autopilot_channel" {
  account_id     = var.new_relic_account_id
  name           = "core_autopilot_channel"
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
# CORE Staging Slack Channel
resource "newrelic_notification_channel" "core_staging_slack_channel" {
  account_id     = var.new_relic_account_id
  name           = "core_staging_slack_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BQ9GMCLER"
    display_value = "help-relibank-core-banking"
  }
}
# CORE Workflow
resource "newrelic_workflow" "core_autopilot_and_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "core_autopilot_and_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.core_banking_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.core_autopilot_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.core_staging_slack_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}
# CORE Policy
resource "newrelic_alert_policy" "core_banking_policy" {
  name                = "ReliBank - Core Banking Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "core_banking_high_response_time_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - High Response Time Health"
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

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "core_banking_high_error_rate_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - High Error Rate Health"
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

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "core_banking_low_throughput_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.core_banking_policy.id
  type                         = "static"
  name                         = "Core Banking - Low Throughput Health"
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

    data_account_id = var.new_relic_account_id

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
    FROM ServiceLevelSnapshot SELECT
      count(*)
    FACET entity.name, entity.guid
    WHERE entity.guid IN (${join(",", [for g in local.relibank_core_banking_sli_guids : "'${g}'"])})
    EOT
    )

    data_account_id = var.new_relic_account_id

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

# PAT Autopilot Channel
resource "newrelic_notification_channel" "pat_autopilot_channel" {
  account_id     = var.new_relic_account_id
  name           = "pat_autopilot_channel"
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
# PAT Staging Slack Channel
resource "newrelic_notification_channel" "pat_staging_slack_channel" {
  account_id     = var.new_relic_account_id
  name           = "pat_staging_slack_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BQB7ZKLBG"
    display_value = "help-relibank-transactions"
  }
}
# PAT Workflow
resource "newrelic_workflow" "pat_autopilot_and_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "pat_autopilot_and_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.pat_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.pat_autopilot_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.pat_staging_slack_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}
# PAT Policy
resource "newrelic_alert_policy" "pat_policy" {
  name                = "ReliBank - Payments & Transactions Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# Transaction Service High Response Time
resource "newrelic_nrql_alert_condition" "pat_transaction_service_high_response_time" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "PAT - Transaction Service High Response Time"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - Payments & Transactions'
    AND entityGuid = '${data.newrelic_entity.transaction_service.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "above"
    threshold             = 200
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "High Response Time | {{ entity_name }}"
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "pat_high_response_time_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - High Response Time Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Transaction SELECT
      percentile(duration, 99) * 1000
    FACET appName AS 'entityName'
    WHERE tags.team = 'ReliBank - Payments & Transactions'
    AND entityGuid != '${data.newrelic_entity.transaction_service.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "pat_high_error_rate_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - High Error Rate Health"
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

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "pat_low_throughput_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.pat_policy.id
  type                         = "static"
  name                         = "Payments & Transactions - Low Throughput Health"
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

    data_account_id = var.new_relic_account_id

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
    FROM ServiceLevelSnapshot SELECT
      count(*)
    FACET entity.name, entity.guid
    WHERE entity.guid IN (${join(",", [for g in local.relibank_pat_sli_guids : "'${g}'"])})
    EOT
    )

    data_account_id = var.new_relic_account_id

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

# PLATFORM Autopilot Channel
resource "newrelic_notification_channel" "platform_autopilot_channel" {
  account_id     = var.new_relic_account_id
  name           = "platform_autopilot_channel"
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
# PLATFORM Staging Slack Channel
resource "newrelic_notification_channel" "platform_staging_slack_channel" {
  account_id     = var.new_relic_account_id
  name           = "platform_staging_slack_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BR7HBJ916"
    display_value = "help-relibank-platform"
  }
}
# PLATFORM Workflow
resource "newrelic_workflow" "platform_autopilot_and_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "platform_autopilot_and_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.platform_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.platform_autopilot_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.platform_staging_slack_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}
# PLATFORM Policy
resource "newrelic_alert_policy" "platform_policy" {
  name                = "ReliBank - Platform Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# APM Response Time
resource "newrelic_nrql_alert_condition" "platform_high_response_time_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - High Response Time Health"
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

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "platform_high_error_rate_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - High Error Rate Health"
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

    data_account_id = var.new_relic_account_id

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
resource "newrelic_nrql_alert_condition" "platform_low_throughput_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.platform_policy.id
  type                         = "static"
  name                         = "Platform - Low Throughput Health"
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

    data_account_id = var.new_relic_account_id

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
    FROM ServiceLevelSnapshot SELECT
      count(*)
    FACET entity.name, entity.guid
    WHERE entity.guid IN (${join(",", [for g in local.relibank_platform_sli_guids : "'${g}'"])})
    EOT
    )

    data_account_id = var.new_relic_account_id

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
    FROM K8sNodeSample SELECT
      filter(uniqueCount(nodeName), WHERE condition.Ready = 1) / uniqueCount(nodeName) * 100
    WHERE entityGuid = '${data.newrelic_entity.relibank_k8s_cluster.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_flow"
  aggregation_delay  = 120
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
    FROM K8sDeploymentSample SELECT
      latest(podsReady)
    FACET entityName
    WHERE NOT (createdAt IS NULL)
    AND tags.team = 'ReliBank - Platform'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "equals"
    threshold             = 0
    threshold_duration    = 21600
    threshold_occurrences = "all"
  }
  fill_option        = "static"
  fill_value         = 0
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
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
    FROM Metric SELECT latest(kafka.broker.uptime)
      FACET entity.name
    WHERE entity.type = 'KAFKABROKER'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "equals"
    threshold             = 0
    threshold_duration    = 3600
    threshold_occurrences = "all"
  }
  fill_option        = "static"
  fill_value         = 0.0
  aggregation_window = 60
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
    FROM Metric SELECT
      latest(kafka.brokers)
    FACET entity.name
    WHERE entity.type = 'KAFKACLUSTER'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "equals"
    threshold             = 0
    threshold_duration    = 3600
    threshold_occurrences = "all"
  }
  fill_option        = "static"
  fill_value         = 0.0
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
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
    FROM Metric SELECT
      max(kafka.prod.msg.count)
    FACET entity.name
    WHERE entity.type = 'KAFKATOPIC'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "equals"
    threshold             = 0
    threshold_duration    = 3600
    threshold_occurrences = "all"
  }
  fill_option        = "static"
  fill_value         = 0.0
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
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
    FROM Metric SELECT latest(sqlserver.database.count)
      FACET entity.name
    WHERE metricName = 'sqlserver.database.count'
    WHERE database.status = 'online'
    WHERE entity.guid = '${data.newrelic_entity.mssql_db360_database.guid}'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_flow"
  aggregation_delay  = 120
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
# Legacy Support Service - assess_payment_risk Error Rate
resource "newrelic_nrql_alert_condition" "before_autopilot_assess_payment_risk" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.before_autopilot_policy.id
  type                         = "static"
  name                         = "Legacy assess_payment_risk - High Transaction Error Rate"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      latest(apm.service.transaction.error.count['count'])
    FACET entity.name AS 'entityName'
    WHERE tags.team = 'ReliBank - AI & Digital Experience'
    AND transactionName = 'WebTransaction/Function/support_service:assess_payment_risk'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "above"
    threshold             = 0
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }
  fill_option        = "static"
  fill_value         = 0
  aggregation_window = 60
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Transaction Errors on 'assess_payment_risk'"
}

### Autopilot + Workflow Automation ###
# Specific policy used to invoke Autopilot + Workflow Automation
resource "newrelic_alert_policy" "apwa_policy" {
  name                = "ReliBank - Autopilot + Workflow Automation Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# Workflow Automation Destination
resource "newrelic_notification_destination" "apwa_destination" {
  account_id = var.new_relic_account_id
  name       = "apwa_destination"
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
# Autopilot Notification Channel
resource "newrelic_notification_channel" "apwa_autopilot_channel" {
  account_id     = var.new_relic_account_id
  name           = "apwa_autopilot_channel"
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
# Workflow Automation Notification Channel
resource "newrelic_notification_channel" "apwa_workflow_channel" {
  account_id     = var.new_relic_account_id
  name           = "apwa_workflow_channel"
  type           = "WORKFLOW_AUTOMATION"
  destination_id = newrelic_notification_destination.apwa_destination.id
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
resource "newrelic_workflow" "apwa_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "apwa_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values    = ["${newrelic_alert_policy.apwa_policy.id}"]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.apwa_autopilot_channel.id
    notification_triggers   = ["ACTIVATED"]
    update_original_message = true
  }

  destination {
    channel_id              = newrelic_notification_channel.apwa_workflow_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING", "OTHER_UPDATES", "PRIORITY_CHANGED"]
    update_original_message = true
  }
}
# NRQL Alert
resource "newrelic_nrql_alert_condition" "apwa_bill_pay_errors" {
  account_id = var.new_relic_account_id
  policy_id  = newrelic_alert_policy.apwa_policy.id
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

### Mobile Alerts ###
# Staging Slack Mobile Notification Channel
resource "newrelic_notification_channel" "staging_slack_relibank_mobile_channel" {
  account_id     = var.new_relic_account_id
  name           = "staging_slack_relibank_mobile_channel"
  type           = "SLACK"
  destination_id = local.staging_slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0C2FHUH07K"
    display_value = "help-relibank-mobile"
  }
}
# Mobile Slack Workflow
resource "newrelic_workflow" "mobile_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "mobile_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.aide_mobile_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.staging_slack_relibank_mobile_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}
# AIDE Mobile Policy
resource "newrelic_alert_policy" "aide_mobile_policy" {
  name                = "ReliBank Mobile - AI & Digital Experience Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}
# ReliBank Mobile Android - Excess Transfer Attempts
resource "newrelic_nrql_alert_condition" "aide_android_excess_transfer_attempts" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.aide_mobile_policy.id
  type                         = "static"
  name                         = "Android Mobile - Excess Transfer Attempts"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Log SELECT
      count(*)
    FACET entity.guid, userEmail
    WHERE entity.guid = '${coalesce(data.newrelic_entity.relibank_mobile_android.guid, "entity-not-found")}'
    AND action = 'transfer_funds_button_pressed'
    EOT
    )

    data_account_id = var.new_relic_account_id

  }

  critical {
    operator              = "above"
    threshold             = 2
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 120
  title_template     = "Excess Transfer Button Presses | {{ entity_name }}"
}

# tags applied across all new relic entities
# local vars used to map teams

locals {
  # ReliBank - AI & Digital Experience team
  # AI agent entities use ignore_not_found and can resolve to a concrete null at plan time if
  # New Relic hasn't discovered them yet - filter those out. Everything else here is either a
  # data source without ignore_not_found (errors loudly if missing, never null) or a resource
  # attribute that is simply unknown-until-apply on first create (never null) - do not filter
  # those, or the whole list's length becomes unknown and breaks count/for_each planning.
  relibank_aide_list = concat(
    [
      data.newrelic_entity.support_service.guid,
      data.newrelic_entity.customer_portal_browser.guid,
      data.newrelic_entity.relibank_mobile_android.guid,
      data.newrelic_entity.relibank_mobile_ios.guid,
      newrelic_service_level.customer_portal_browser_success_sl.sli_guid,
      newrelic_service_level.support_service_success_sl.sli_guid,
      newrelic_synthetics_script_monitor.relibank_login_check.id,
      newrelic_workload.relibank_aide_workload.guid,
      newrelic_nrql_alert_condition.aide_android_excess_transfer_attempts.entity_guid,
      newrelic_nrql_alert_condition.aide_chat_with_model.entity_guid,
      newrelic_nrql_alert_condition.aide_high_response_time.entity_guid,
      newrelic_nrql_alert_condition.aide_high_error_rate.entity_guid,
      newrelic_nrql_alert_condition.aide_low_throughput.entity_guid,
      newrelic_nrql_alert_condition.aide_high_inp.entity_guid,
      newrelic_nrql_alert_condition.aide_high_lcp.entity_guid,
      newrelic_nrql_alert_condition.high_js_error_rate.entity_guid,
      newrelic_nrql_alert_condition.high_page_load_time.entity_guid,
      newrelic_nrql_alert_condition.aide_ai_agent_health.entity_guid,
      newrelic_nrql_alert_condition.aide_ai_tool_health.entity_guid,
      newrelic_nrql_alert_condition.aide_service_level_health.entity_guid,
      newrelic_nrql_alert_condition.aide_synthetic_failing.entity_guid,
      newrelic_nrql_alert_condition.legacy_chat_with_model.entity_guid
    ],
    [for guid in [
      data.newrelic_entity.coordinator_ai_agent.guid,
      data.newrelic_entity.specialist_ai_agent.guid,
      data.newrelic_entity.synthesizer_ai_agent.guid,
      data.newrelic_entity.delegate_to_specialist_ai_tool.guid,
    ] : guid if guid != null]
  )
  # ReliBank - Core Banking team
  relibank_core_banking_list = concat(
    [
      data.newrelic_entity.accounts_service.guid,
      data.newrelic_entity.auth_service.guid,
      newrelic_service_level.accounts_service_success_sl.sli_guid,
      newrelic_service_level.auth_service_success_sl.sli_guid,
      newrelic_workload.relibank_core_banking_workload.guid,
      newrelic_nrql_alert_condition.core_banking_high_response_time.entity_guid,
      newrelic_nrql_alert_condition.core_banking_high_error_rate.entity_guid,
      newrelic_nrql_alert_condition.core_banking_low_throughput.entity_guid,
      newrelic_nrql_alert_condition.core_banking_service_level_health.entity_guid
    ]
  )
  # ReliBank - Payments & Transactions team
  relibank_pat_list = concat(
    [
      data.newrelic_entity.bill_pay_service.guid,
      data.newrelic_entity.notifications_service.guid,
      data.newrelic_entity.transaction_service.guid,
      newrelic_service_level.bill_pay_service_success_sl.sli_guid,
      newrelic_service_level.notifications_service_success_sl.sli_guid,
      newrelic_service_level.transaction_service_success_sl.sli_guid,
      newrelic_workload.relibank_pat_workload.guid,
      newrelic_nrql_alert_condition.pat_high_response_time.entity_guid,
      newrelic_nrql_alert_condition.pat_high_error_rate.entity_guid,
      newrelic_nrql_alert_condition.pat_low_throughput.entity_guid,
      newrelic_nrql_alert_condition.pat_service_level_health.entity_guid,
      newrelic_nrql_alert_condition.wa_bill_pay_errors.entity_guid
    ]
  )
  # ReliBank - Platform team
  # Same split as relibank_aide_list above: only the ignore_not_found kafka topic / mssql
  # entities are filtered for null; everything else is left as a plain list.
  relibank_platform_list = concat(
    [
      data.newrelic_entity.event_scheduler_service.guid,
      # risk-assessment-service is a 'rogue service' for ebpf/platform
      data.newrelic_entity.risk_assessment_service.guid,
      data.newrelic_entity.relibank_k8s_cluster.guid,
      data.newrelic_entity.accounts_db_k8s_dep.guid,
      data.newrelic_entity.accounts_service_k8s_dep.guid,
      data.newrelic_entity.auth_service_k8s_dep.guid,
      data.newrelic_entity.bill_pay_service_k8s_dep.guid,
      data.newrelic_entity.coredns_k8s_dep.guid,
      data.newrelic_entity.coredns_autoscaler_k8s_dep.guid,
      data.newrelic_entity.frontend_service_k8s_dep.guid,
      data.newrelic_entity.ingress_nginx_controller_k8s_dep.guid,
      data.newrelic_entity.kafka_k8s_dep.guid,
      data.newrelic_entity.kube_state_metrics_k8s_dep.guid,
      data.newrelic_entity.nri_kube_events_k8s_dep.guid,
      data.newrelic_entity.nri_metadata_injection_k8s_dep.guid,
      data.newrelic_entity.nri_prometheus_k8s_dep.guid,
      data.newrelic_entity.nri_ksm_k8s_dep.guid,
      data.newrelic_entity.notifications_service_k8s_dep.guid,
      data.newrelic_entity.risk_assessment_service_k8s_dep.guid,
      data.newrelic_entity.scheduler_service_k8s_dep.guid,
      data.newrelic_entity.support_service_k8s_dep.guid,
      data.newrelic_entity.transaction_service_k8s_dep.guid,
      data.newrelic_entity.zookeeper_k8s_dep.guid,
      newrelic_service_level.event_scheduler_service_success_sl.sli_guid,
      newrelic_workload.relibank_platform_workload.guid,
      newrelic_nrql_alert_condition.platform_high_response_time.entity_guid,
      newrelic_nrql_alert_condition.platform_high_error_rate.entity_guid,
      newrelic_nrql_alert_condition.platform_low_throughput.entity_guid,
      newrelic_nrql_alert_condition.platform_service_level_health.entity_guid,
      newrelic_nrql_alert_condition.platform_k8s_cluster_health.entity_guid,
      newrelic_nrql_alert_condition.platform_k8s_deployment_health.entity_guid,
      newrelic_nrql_alert_condition.platform_kafka_broker_health.entity_guid,
      newrelic_nrql_alert_condition.platform_kafka_cluster_health.entity_guid,
      newrelic_nrql_alert_condition.platform_kafka_topic_health.entity_guid,
      newrelic_nrql_alert_condition.platform_database_health.entity_guid
    ],
    [for guid in [
      data.newrelic_entity.relibank_kafka_broker.guid,
      data.newrelic_entity.relibank_kafka_cluster.guid,
      data.newrelic_entity.consumer_offsets_kafka_topic.guid,
      data.newrelic_entity.bill_payments_kafka_topic.guid,
      data.newrelic_entity.bill_payments_declined_kafka_topic.guid,
      data.newrelic_entity.card_payments_kafka_topic.guid,
      data.newrelic_entity.card_payments_declined_kafka_topic.guid,
      data.newrelic_entity.payment_cancellations_kafka_topic.guid,
      data.newrelic_entity.payment_due_notifications_kafka_topic.guid,
      data.newrelic_entity.payment_declined_kafka_topic.guid,
      data.newrelic_entity.recurring_payments_kafka_topic.guid,
      data.newrelic_entity.mssql_ohi_database.guid,
      data.newrelic_entity.mssql_db360_database.guid,
    ] : guid if guid != null]
  )
  # All teams
  relibank_all_teams_list = concat(
    [
      newrelic_one_dashboard_json.relibank_summary.guid,
      newrelic_one_dashboard_json.relibank_bill_pay_metrics.guid
    ]
  )
}

### TEAM ASSIGNMENTS ###
# ReliBank - AI & Digital Experience team
resource "newrelic_entity_tags" "relibank_aide_tags" {
  count = length(local.relibank_aide_list)
  guid  = local.relibank_aide_list[count.index]

  tag {
    key    = "team"
    values = ["ReliBank - AI & Digital Experience"]
  }
  tag {
    key    = "deploymentTier"
    values = [var.demo_environment]
  }
  tag {
    key    = "heroChannel"
    values = ["help-relibank-ai-and-exp"]
  }
  tag {
    key    = "githubRepo"
    values = ["https://github.com/newrelic/relibank"]
  }
  tag {
    key    = "appStack"
    values = ["relibank"]
  }
  tag {
    key    = "managedBy"
    values = ["terraform"]
  }

  depends_on = [local.relibank_aide_list]
}

# ReliBank - Core Banking team
resource "newrelic_entity_tags" "relibank_core_banking_tags" {
  count = length(local.relibank_core_banking_list)
  guid  = local.relibank_core_banking_list[count.index]

  tag {
    key    = "team"
    values = ["ReliBank - Core Banking"]
  }
  tag {
    key    = "deploymentTier"
    values = [var.demo_environment]
  }
  tag {
    key    = "heroChannel"
    values = ["help-relibank-core-banking"]
  }
  tag {
    key    = "githubRepo"
    values = ["https://github.com/newrelic/relibank"]
  }
  tag {
    key    = "appStack"
    values = ["relibank"]
  }
  tag {
    key    = "managedBy"
    values = ["terraform"]
  }

  depends_on = [local.relibank_core_banking_list]
}

# ReliBank - Payments & Transactions team
resource "newrelic_entity_tags" "relibank_pat_tags" {
  count = length(local.relibank_pat_list)
  guid  = local.relibank_pat_list[count.index]

  tag {
    key    = "team"
    values = ["ReliBank - Payments & Transactions"]
  }
  tag {
    key    = "deploymentTier"
    values = [var.demo_environment]
  }
  tag {
    key    = "heroChannel"
    values = ["help-relibank-transactions"]
  }
  tag {
    key    = "githubRepo"
    values = ["https://github.com/newrelic/relibank"]
  }
  tag {
    key    = "appStack"
    values = ["relibank"]
  }
  tag {
    key    = "managedBy"
    values = ["terraform"]
  }

  depends_on = [local.relibank_pat_list]
}

# ReliBank - Platform team
resource "newrelic_entity_tags" "relibank_platform_tags" {
  count = length(local.relibank_platform_list)
  guid  = local.relibank_platform_list[count.index]

  tag {
    key    = "team"
    values = ["ReliBank - Platform"]
  }
  tag {
    key    = "deploymentTier"
    values = [var.demo_environment]
  }
  tag {
    key    = "heroChannel"
    values = ["help-relibank-platform"]
  }
  tag {
    key    = "githubRepo"
    values = ["https://github.com/newrelic/relibank"]
  }
  tag {
    key    = "appStack"
    values = ["relibank"]
  }
  tag {
    key    = "managedBy"
    values = ["terraform"]
  }

  depends_on = [local.relibank_platform_list]
}

### ALL TEAMS ###
# resources belonging to every team and need the full list applied
resource "newrelic_entity_tags" "relibank_all_teams_tags" {
  count = length(local.relibank_all_teams_list)
  guid  = local.relibank_all_teams_list[count.index]

  tag {
    key    = "team"
    values = ["ReliBank - AI & Digital Experience", "ReliBank - Core Banking", "ReliBank - Payments & Transactions", "ReliBank - Platform"]
  }
  tag {
    key    = "deploymentTier"
    values = [var.demo_environment]
  }
  tag {
    key    = "appStack"
    values = ["relibank"]
  }
  tag {
    key    = "managedBy"
    values = ["terraform"]
  }

  depends_on = [local.relibank_all_teams_list]
}

# entities created through instrumentation or org-level resources that are not in the associated state file
###
# data.newrelic_entity.accounts_service.guid
# data.newrelic_entity.auth_service.guid
# data.newrelic_entity.bill_pay_service.guid
# data.newrelic_entity.event_scheduler_service.guid
# data.newrelic_entity.notifications_service.guid
# data.newrelic_entity.support_service.guid
# data.newrelic_entity.transaction_service.guid
# data.newrelic_entity.customer_portal_browser.guid
# data.newrelic_entity.risk_assessment_service.guid
# data.newrelic_entity.coordinator_ai_agent.guid
# data.newrelic_entity.specialist_ai_agent.guid
# data.newrelic_entity.synthesizer_ai_agent.guid
# data.newrelic_entity.delegate_to_specialist_ai_tool.guid
# data.newrelic_entity.relibank_k8s_cluster.guid
# data.newrelic_entity.accounts_db_k8s_dep.guid
# data.newrelic_entity.accounts_service_k8s_dep.guid
# data.newrelic_entity.auth_service_k8s_dep.guid
# data.newrelic_entity.bill_pay_service_k8s_dep.guid
# data.newrelic_entity.coredns_k8s_dep.guid
# data.newrelic_entity.coredns_autoscaler_k8s_dep.guid
# data.newrelic_entity.frontend_service_k8s_dep.guid
# data.newrelic_entity.ingress_nginx_controller_k8s_dep.guid
# data.newrelic_entity.kafka_k8s_dep.guid
# data.newrelic_entity.kube_state_metrics_k8s_dep.guid
# data.newrelic_entity.nri_kube_events_k8s_dep.guid
# data.newrelic_entity.nri_metadata_injection_k8s_dep.guid
# data.newrelic_entity.nri_prometheus_k8s_dep.guid
# data.newrelic_entity.nri_ksm_k8s_dep.guid
# data.newrelic_entity.notifications_service_k8s_dep.guid
# data.newrelic_entity.risk_assessment_service_k8s_dep.guid
# data.newrelic_entity.scheduler_service_k8s_dep.guid
# data.newrelic_entity.support_service_k8s_dep.guid
# data.newrelic_entity.transaction_service_k8s_dep.guid
# data.newrelic_entity.zookeeper_k8s_dep.guid
# data.newrelic_entity.relibank_kafka_broker.guid
# data.newrelic_entity.relibank_kafka_cluster.guid
# data.newrelic_entity.consumer_offsets_kafka_topic.guid
# data.newrelic_entity.bill_payments_kafka_topic.guid
# data.newrelic_entity.bill_payments_declined_kafka_topic.guid
# data.newrelic_entity.card_payments_kafka_topic.guid
# data.newrelic_entity.card_payments_declined_kafka_topic.guid
# data.newrelic_entity.payment_cancellations_kafka_topic.guid
# data.newrelic_entity.payment_due_notifications_kafka_topic.guid
# data.newrelic_entity.payment_declined_kafka_topic.guid
# data.newrelic_entity.recurring_payments_kafka_topic.guid
# data.newrelic_entity.mssql_ohi_database.guid
# data.newrelic_entity.mssql_db360_database.guid
# data.newrelic_entity.relibank_mobile_android  //TODO
# data.newrelic_entity.relibank_mobile_ios      //TODO
# data.newrelic_notification_destination.autopilot_destination.id
###

### APM APPLICATIONS ###
data "newrelic_entity" "accounts_service" {
  name       = "${var.app_name} - Accounts Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "auth_service" {
  name       = "${var.app_name} - Auth Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "bill_pay_service" {
  name       = "${var.app_name} - Bill Pay Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "event_scheduler_service" {
  name       = "${var.app_name} - Event Scheduler Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "notifications_service" {
  name       = "${var.app_name} - Notifications Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "support_service" {
  name       = "${var.app_name} - Support Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "transaction_service" {
  name       = "${var.app_name} - Transaction Service"
  domain     = "APM"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}

### BROWSER APPLICATION ###
data "newrelic_entity" "customer_portal_browser" {
  name       = "Relibank - Customer Portal"
  domain     = "BROWSER"
  type       = "APPLICATION"
  account_id = var.new_relic_account_id
}

### eBPF SERVICES ###
data "newrelic_entity" "risk_assessment_service" {
  name       = "risk-assessment-service"
  domain     = "EXT"
  type       = "SERVICE"
  account_id = var.new_relic_account_id
}

### AI AGENTS ###
data "newrelic_entity" "coordinator_ai_agent" {
  name             = "coordinator"
  domain           = "APM"
  type             = "AI_AGENT"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "specialist_ai_agent" {
  name             = "specialist"
  domain           = "APM"
  type             = "AI_AGENT"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "synthesizer_ai_agent" {
  name             = "synthesizer"
  domain           = "APM"
  type             = "AI_AGENT"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### AI TOOLS ###
data "newrelic_entity" "delegate_to_specialist_ai_tool" {
  name             = "delegate_to_specialist"
  domain           = "APM"
  type             = "AI_TOOL"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### K8S CLUSTER ###
data "newrelic_entity" "relibank_k8s_cluster" {
  name       = "relibank-${var.demo_environment}"
  domain     = "INFRA"
  type       = "KUBERNETESCLUSTER"
  account_id = var.new_relic_account_id
}

### K8S DEPLOYMENTS ###
data "newrelic_entity" "accounts_db_k8s_dep" {
  name       = "accounts-db"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "accounts_service_k8s_dep" {
  name       = "accounts-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "auth_service_k8s_dep" {
  name       = "auth-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "bill_pay_service_k8s_dep" {
  name       = "bill-pay-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "coredns_k8s_dep" {
  name       = "coredns"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "coredns_autoscaler_k8s_dep" {
  name       = "coredns-autoscaler"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "frontend_service_k8s_dep" {
  name       = "frontend-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "ingress_nginx_controller_k8s_dep" {
  name       = "ingress-nginx-controller"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "kafka_k8s_dep" {
  name       = "kafka"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "kube_state_metrics_k8s_dep" {
  name       = "newrelic-bundle-kube-state-metrics"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "nri_kube_events_k8s_dep" {
  name       = "newrelic-bundle-nri-kube-events"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "nri_metadata_injection_k8s_dep" {
  name       = "newrelic-bundle-nri-metadata-injection"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "nri_prometheus_k8s_dep" {
  name       = "newrelic-bundle-nri-prometheus"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "nri_ksm_k8s_dep" {
  name       = "newrelic-bundle-nrk8s-ksm"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "notifications_service_k8s_dep" {
  name       = "notifications-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "risk_assessment_service_k8s_dep" {
  name       = "risk-assessment-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "scheduler_service_k8s_dep" {
  name       = "scheduler-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "support_service_k8s_dep" {
  name       = "support-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "transaction_service_k8s_dep" {
  name       = "transaction-service"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}
data "newrelic_entity" "zookeeper_k8s_dep" {
  name       = "zookeeper"
  domain     = "INFRA"
  type       = "KUBERNETES_DEPLOYMENT"
  account_id = var.new_relic_account_id
}

### KAFKA BROKER ###
data "newrelic_entity" "relibank_kafka_broker" {
  name             = "BrokerId:1 (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKABROKER"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### KAFKA CLUSTER ###
data "newrelic_entity" "relibank_kafka_cluster" {
  name             = "relibank-kafka"
  domain           = "INFRA"
  type             = "KAFKACLUSTER"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### KAFKA TOPICS ###
data "newrelic_entity" "consumer_offsets_kafka_topic" {
  name             = "__consumer_offsets (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "bill_payments_kafka_topic" {
  name             = "bill_payments (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "bill_payments_declined_kafka_topic" {
  name             = "bill_payments_declined (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "card_payments_kafka_topic" {
  name             = "card_payments (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "card_payments_declined_kafka_topic" {
  name             = "card_payments_declined (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "payment_cancellations_kafka_topic" {
  name             = "payment_cancellations (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "payment_due_notifications_kafka_topic" {
  name             = "payment_due_notifications (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "payment_declined_kafka_topic" {
  name             = "payment-declined (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
data "newrelic_entity" "recurring_payments_kafka_topic" {
  name             = "recurring_payments (relibank-kafka)"
  domain           = "INFRA"
  type             = "KAFKATOPIC"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### DATABASES ###
data "newrelic_entity" "mssql_ohi_database" {
  name       = "ms-instance:mssql-0"
  domain     = "INFRA"
  type       = "MSSQLINSTANCE"
  account_id = var.new_relic_account_id
  tag {
    key   = "integrationName"
    value = "com.newrelic.mssql"
  }
  ignore_not_found = true
}
data "newrelic_entity" "mssql_db360_database" {
  name       = "mssql-0-${var.demo_environment}"
  domain     = "INFRA"
  type       = "MSSQLINSTANCE"
  account_id = var.new_relic_account_id
  tag {
    key   = "instrumentation.provider"
    value = "opentelemetry"
  }
  ignore_not_found = true
}

//TODO - add mobile entities once they're live
//### MOBILE APPS ###
//data "newrelic_entity" "relibank_mobile_android" {
//  name             = "relibank-mobile-android"
//  domain           = "MOBILE"
//  type             = "APPLICATION"
//  account_id       = var.new_relic_account_id
//}
//data "newrelic_entity" "relibank_mobile_ios" {
//  name             = "relibank-mobile-ios"
//  domain           = "MOBILE"
//  type             = "APPLICATION"
//  account_id       = var.new_relic_account_id
//}

### CROSS-ACCOUNT DESTINATION ###
data "newrelic_notification_destination" "autopilot_destination" {
  exact_name = "sre_agent_destination"
  scope {
    type = "ORGANIZATION"
    id   = "5e1ae959-709c-48f6-9b54-8863939669b7"
  }
}
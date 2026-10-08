# workflow automation definitions
###
# newrelic_workflow_automation.github_scale_relibank_service.id | version
###

# github_scale_relibank_service
resource "newrelic_workflow_automation" "github_scale_relibank_service" {
  name       = "github_scale_relibank_service"
  scope_id   = var.new_relic_account_id
  scope_type = "ACCOUNT"
  definition = file("workflow_automations/github_scale_relibank_service.tftpl")
}
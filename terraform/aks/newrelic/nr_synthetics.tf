# utilizes template files to load scripts for browser and API checks
###
# newrelic_synthetics_script_monitor.relibank_login_check.id
###

# scripted check to login and validate the dashboard loads
resource "newrelic_synthetics_script_monitor" "relibank_login_check" {
  status               = "ENABLED"
  name                 = "${var.app_name} - Login Check"
  type                 = "SCRIPT_BROWSER"
  period               = "EVERY_10_MINUTES"
  locations_public     = ["AP_SOUTH_1", "US_WEST_2", "EU_WEST_1"]
  runtime_type         = "CHROME_BROWSER"
  runtime_type_version = "LATEST"
  script_language      = "JAVASCRIPT"

  script = templatefile("${path.module}/scripts/relibank_login_check.tftpl", {
    target_url = "https://${var.demo_environment}.relibankdemo.com/"
  })
}

# TMM: Replace these placeholder ping + script monitors with real coverage (status pages,
# checkout flow, error scenarios, etc.). Script bodies live under `./scripts/` as `.tftpl`
# files referenced via `templatefile(...)`. Demogorgon's nr_synthetics.tf is the reference.

resource "newrelic_synthetics_monitor" "placeholder_ping" {
  status                    = "ENABLED"
  name                      = "${var.app_name} - Placeholder Ping"
  period                    = "EVERY_5_MINUTES"
  uri                       = "https://${var.demo_environment}.relibankdemo.com/"
  type                      = "SIMPLE"
  locations_public          = ["US_WEST_2"]
  runtime_type              = "NODE_API"
  runtime_type_version      = "16.10"
  treat_redirect_as_failure = false
  bypass_head_request       = true
  verify_ssl                = true
}

resource "newrelic_synthetics_script_monitor" "placeholder_script" {
  status               = "ENABLED"
  name                 = "${var.app_name} - Placeholder Script Monitor"
  type                 = "SCRIPT_API"
  period               = "EVERY_30_MINUTES"
  locations_public     = ["US_WEST_2"]
  runtime_type         = "NODE_API"
  runtime_type_version = "16.10"

  script = templatefile("${path.module}/scripts/placeholder.tftpl", {
    demo_environment = var.demo_environment
  })
}

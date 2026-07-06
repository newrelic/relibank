# Dashboards

# TMM: Drop dashboard JSON templates here as `<name>.json.tftpl` and wire each one up with a `newrelic_one_dashboard_json` resource in `../nr_dashboards.tf` using `templatefile("${path.module}/dashboards/<name>.json.tftpl", { ... })`. Demogorgon's `applications/microservices-demo/terraform/newrelic/dashboards/` is the reference layout.

Template-variable conventions used by the existing placeholder:

- `${app_name}` — NR display root, e.g. `ReliBank (Sandbox)`
- `${account_id}` — numeric NR account ID (pass via `tonumber(var.new_relic_account_id)`)
- `${support_service_guid}` — APM entity GUID resolved via `data.newrelic_entity.support_service` in `../nr_entities.tf`

Add new template vars as needed — the `templatefile(...)` call in `../nr_dashboards.tf` controls the var set passed in.

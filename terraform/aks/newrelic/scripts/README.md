# Synthetics scripts

# TMM: Drop synthetic-monitor script templates here as `<name>.tftpl` and wire each one up with a `newrelic_synthetics_script_monitor` resource in `../nr_synthetics.tf` using `templatefile("${path.module}/scripts/<name>.tftpl", { ... })`. Demogorgon's `applications/microservices-demo/terraform/newrelic/scripts/` is the reference layout.

Template-variable conventions used by the existing placeholder:

- `${demo_environment}` — env name (sandbox, staging, prod, analysts); used to build the target URL

Add new template vars as needed — the `templatefile(...)` call in `../nr_synthetics.tf` controls the var set passed in. SIMPLE / ping monitors don't take a script body, so they stay inline in `nr_synthetics.tf` and don't belong in this directory.

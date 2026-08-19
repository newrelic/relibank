# OTel collector configs (mssql / kafka)

These 4 files are duplicated here — not read cross-tree via
`file("${path.module}/../../../k8s/base/...")` — to match this repo's existing convention:
Terraform modules own their own template files (see `terraform/aks/newrelic/scripts/` and
`terraform/aks/newrelic/dashboards/`), they don't reach into the parallel `k8s/` kustomize tree.

`otel-collector-kafka-config.yaml`, `kafka-jmx-config.yaml`, and `internal-telemetry-config.yaml`
are copies of the `data` values from the legacy kustomize ConfigMaps under
`k8s/base/configs/{otel-collector-kafka,kafka-jmx,internal-telemetry}-config.yaml` (the manifests
the single-namespace `events` cluster still runs), read as-is via `file(...)` in `../main.tf`. If
those legacy manifests change, re-sync these files by hand — there's no automatic link.

`nrdot-collector-mssql-config.yaml` is **not** copied from `main`'s current
`k8s/base/configs/nrdot-collector-mssql-config.yaml` — that file is still on the older
`newrelicsqlserver` receiver. This one uses the `nrsqlserver` receiver instead, sourced from
`db360-new-image-rebased` (an unmerged branch that's what `events` is actually running today —
`main`'s `k8s/base` copy is stale relative to production, a separate, still-open gap this port
doesn't fix). It's read via `file(...)` + `yamldecode(...)`, then patched in `../main.tf`
(`local.nrdot_mssql_config_patched`) with one Terraform-only change that doesn't apply to the
legacy single-namespace `events` deployment:

- `receivers.nrsqlserver.server` — legacy manifest has bare `"mssql-0"`. `events` gets away with
  that because its legacy `mssql-deployment.yaml` defines a *separate* `Service` literally named
  `mssql-0` (a `LoadBalancer`, for external/CI access) — bare `mssql-0` resolves as an ordinary
  Service DNS lookup, not StatefulSet pod-DNS. `app_module` has no such Service, only the
  headless `mssql` one, so pod-DNS is the only path here: patched to `"mssql-0.mssql"`
  (`<pod>.<governing-service>`), which headless services always populate.

The config's own `resource/mssql_identity` processor (stamps `host.name`/`host.id` to
`mssql-0-${env:RELIBANK_ENVIRONMENT}`) needs no patching — `../main.tf` just feeds
`RELIBANK_ENVIRONMENT` a value (`var.demo_environment`, e.g. `"sandbox"`) via the Deployment's
env, same mechanism `db360-new-image-rebased`'s legacy-manifest changes use (`"local"`/`"events"`,
via a per-overlay kustomize patch not present on `main`). Deliberately env-only, not color-aware —
one stable MSSQLINSTANCE entity per environment, shared by whichever color is live, not a
separate entity per color.

Also, `receivers.nrsqlserver.metrics` has 15 keys removed relative to `db360-new-image-rebased`'s
version of this file: `nrsqlserver` v0.157.2 (bundled in `nrdot-collector-releases` 2.0.0, what
`otel_collector_mssql/Dockerfile`'s dynamic "latest" fetch resolves to today) dropped them with no
replacement, relative to v0.156.1 (bundled in `1.21.1`, what `events`'s frozen image actually
runs) — confirmed by diffing `metadata.yaml` for both versions on
`github.com/newrelic-forks/opentelemetry-collector-contrib`. Two have same-purpose replacements
already/newly enabled (`sqlserver.memory.area`, `sqlserver.error.rate`); 13 don't. See the
`# NOTE:` comments inline in the file. If `nrdot-collector-releases` ships another breaking
metrics change, expect this to need re-trimming — or pin `NRDOT_VERSION` in the Dockerfile
instead of tracking "latest".

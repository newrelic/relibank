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

#### Why the processor also touches `server.address`/`service.instance.id`/`server.port`

Added 2026-09-15: staging/prod (on `nrsqlserver` `2.4.0`/`2.5.0`, fresher builds than sandbox's
frozen `2.0.0`) both synthesized as the colliding `mssql-0.mssql:1433` entity despite `host.id`
being verified correct via NRQL. Those receiver versions emit `server.address` (the literal
connection endpoint) and a `service.instance.id` auto-populated as `<server>:<port>` — same
literal value, different keys — and NR's `MSSQLINSTANCE` synthesis prefers either over `host.id`
when present.

Fixing this took three live-verified attempts in staging, in order, because each one changed
observed behavior in a different way:
1. Deleting only `server.address`/`server.port` (keeping `service.instance.id`): entity still
   collided, now keyed on `service.instance.id` instead.
2. Also deleting `service.instance.id`: no identifying field was left for synthesis to use at
   all — the data went **orphaned** (null `entity.guid`, confirmed for 10+ minutes, not just
   synthesis lag), worse than colliding.
3. **Overriding** `server.address`/`service.instance.id` to the same value as `host.id` (deleting
   only the now-unpaired `server.port`) is what actually worked: whichever field synthesis keys
   on, they all resolve to the same name, and nothing required is left absent.

Sandbox's older receiver doesn't emit `server.address` (it does have `service.instance.id`, but
its entity predates that and apparently isn't renamed by it — host.id-keyed matching for an
already-established entity looks more lenient than first-time synthesis). Same "latest"
moving-target risk as the metrics-key drift below: expect this to need revisiting on the next
receiver bump that changes emitted resource attributes — verify against the live entity after any
future change here, the config diff alone is not proof.

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

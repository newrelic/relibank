# relibank-telemetry-gateway

An OpenTelemetry Collector (contrib, pinned by digest) that receives logs from external producers and fans them out:
audit logs go to `compliance-archive` and to New Relic, everything else goes to New Relic only. It exists so the
collector's own telemetry can show queue saturation, export failures, queue drops and receiver refusals in New Relic
Collector Observability when the archive is throttled (scenario-service `archive-throttling`). NR-638736.

```
producer --HTTPS + token--> /otlp/ (nginx proxy) --> :4318 relibank-telemetry-gateway
                                                         |-- audit logs --> compliance-archive:5008   (queue, retries)
                                                         '-- all logs ----> New Relic OTLP
```

## Files

| File | What it is |
|---|---|
| `config.yaml` | Pipelines only: receivers, `memory_limiter`, routing connector, the two exporters. Baked into the image at `/etc/otelcol/config.yaml`. |
| `Dockerfile` | The pinned collector image plus `config.yaml`. The license key is a build arg, like the other collectors. |

The collector's own telemetry is **not** in `config.yaml`. It is loaded as a second `--config` from the shared
`internal-telemetry-config` (the same way `otel-collector-kafka` does it), with `INTERNAL_TELEMETRY_SERVICE_NAME=relibank-telemetry-gateway`.
That file is never edited here.

```
--config=/etc/otelcol/config.yaml  --config=/conf/internal-telemetry-config.yaml
```

## Where it runs

- **Local (`skaffold dev`):** `k8s/overlays/dev/relibank-telemetry-gateway.yaml` (dev overlay only; `k8s/base` is untouched).
- **AKS:** Terraform in `catapult-service` (`relibank_deployer/terraform/aks/app_module`). It mounts a ConfigMap over `/etc/otelcol/config.yaml`
  built from `templates/otel-collector-gateway-config.yaml`, which is a **copy of `config.yaml`. Keep the two in sync by hand.**

## The values that matter, and where they came from

Measured in the Phase 0 spike with 1,200 logs a minute (15 audit + 5 other logs a second). T is minutes after the archive starts refusing.

| Setting | Value | Effect |
|---|---|---|
| `sending_queue.sizer` / `queue_size` | `items` / 6000 | Queue 95% full at about T+6.5. |
| `retry_on_failure.max_elapsed_time` | 180 s | Export failures are first counted when this runs out (90 s gave T+1.5). Untested at 180 s. |
| `block_on_overflow` | `false` | A full queue fails the enqueue instead of waiting. |
| No batch step on the archive pipeline | on purpose | The failed enqueue goes back to the receiver: queue drops and receiver refusals start together (T+6.8) and the New Relic copy of audit logs is starved. |
| `memory_limiter` | 256 MiB / spike 64 | Below the 512 Mi container limit. |

The exporter honors `Retry-After` from the archive's 429 and 503 answers. All values are starting points to **calibrate in sandbox**
against the real producer.

## Check the config

```bash
IMG='otel/opentelemetry-collector-contrib:0.145.0@sha256:a7343f01869071ea3f4c5e1e97df1bb1b3c4d5c77247db80e053a80b9df530c4'
# extract the shared telemetry config from its ConfigMap, then validate both files together
awk '/internal-telemetry-config.yaml: \|/{f=1;next} f{sub(/^    /,""); print}' k8s/base/configs/internal-telemetry-config.yaml > /tmp/internal-telemetry.yaml
docker run --rm -e NEW_RELIC_LICENSE_KEY=placeholder -e INTERNAL_TELEMETRY_SERVICE_NAME=relibank-telemetry-gateway \
  -v "$PWD/otel_collector_gateway/config.yaml:/c1.yaml:ro" -v /tmp/internal-telemetry.yaml:/c2.yaml:ro \
  "$IMG" validate --config=/c1.yaml --config=/c2.yaml; echo "exit $?"   # 0 = valid
```

## Producer contract (draft, to agree with the producer's owner)

- `POST https://<env>.relibankdemo.com/otlp/v1/logs`, OTLP/HTTP, header `Authorization: Bearer <OTLP_INGEST_TOKEN>`.
- About 1,200 logs a minute in requests of about 10 logs. Audit logs carry the attribute `log.type = "audit"` (placeholder name).
- On 429 or 503 the producer should honor `Retry-After`.

## Open items

- Collector distro: contrib 0.145.0 today; the ticket recommends NRDOT >= 2.7.3. The exporter name `otlphttp` is deprecated on 0.145.0
  (kept because older NRDOT builds may not know `otlp_http`).
- Whether receiver refusals should come later than queue drops (the ticket says T+20, this design gives T+6.8).

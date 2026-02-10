# OpenTelemetry Kafka Collector

Custom OpenTelemetry Collector for monitoring Kafka with New Relic, including JMX-based metrics collection for both Kafka broker metrics and JVM telemetry.

## Overview

This collector is specifically configured to monitor Kafka in Kubernetes using:
- **JMX Receiver** - Scrapes Kafka broker and JVM metrics via JMX
- **Kafka Metrics Receiver** - Collects Kafka protocol-level metrics
- **Internal Telemetry** - Monitors the collector itself

All metrics are exported to New Relic via OTLP.

## Architecture

```
┌──────────────────────────────────────────┐
│   Kafka Broker (kafka:29092)            │
│   JMX Endpoint: kafka:9999               │
│   - Kafka metrics (topics, partitions)  │
│   - JVM metrics (GC, memory, threads)   │
└──────────────────────────────────────────┘
                 │
                 │ JMX/RMI
                 ▼
┌──────────────────────────────────────────┐
│   OTel Collector (otel-collector-kafka) │
│                                          │
│   Receivers:                             │
│   ├─ jmx/kafka_broker-1                 │
│   └─ kafkametrics                        │
│                                          │
│   Processors:                            │
│   ├─ resourcedetection                   │
│   ├─ batch                               │
│   └─ transforms/filters                  │
│                                          │
│   Exporters:                             │
│   └─ otlp/newrelic                       │
└──────────────────────────────────────────┘
                 │
                 │ OTLP/HTTP
                 ▼
┌──────────────────────────────────────────┐
│   New Relic (otlp.nr-data.net)          │
│   Entity: relibank-kafka-collector       │
└──────────────────────────────────────────┘
```

## Container Image

### Base Image
- **Runtime:** `eclipse-temurin:17-jre`
- **Architecture:** Multi-arch (arm64 for Apple Silicon, amd64 for production)

### Components
1. **OpenTelemetry Collector Contrib** v0.145.0
   - Downloaded from official releases
   - Includes JMX receiver and Kafka metrics receiver

2. **JMX Scraper JAR** v1.52.0
   - From `opentelemetry-java-contrib`
   - Enables JMX metric collection with YAML-based configuration
   - Located at: `/opt/opentelemetry-jmx-scraper.jar`

3. **New Relic License Key**
   - Baked into image at build time via `ARG` and `ENV`
   - Source: `skaffold.env` → `skaffold.yaml` buildArgs → Dockerfile

### Build Process

The image is built automatically by Skaffold:

```yaml
# From skaffold.yaml
- image: otel-collector-kafka
  context: .
  docker:
    dockerfile: otel_collector_kafka/Dockerfile
    buildArgs:
      NEW_RELIC_LICENSE_KEY: "{{.NEW_RELIC_LICENSE_KEY}}"
```

**Dockerfile highlights:**
```dockerfile
# Multi-stage: Download binaries
FROM alpine:latest as prep
ARG OTEL_VERSION=0.145.0
ARG TARGETARCH  # Docker sets this: arm64 or amd64
ADD "https://github.com/open-telemetry/.../otelcol-contrib_${OTEL_VERSION}_linux_${TARGETARCH}.tar.gz" /otelcontribcol

# Final image: Eclipse Temurin JRE
FROM eclipse-temurin:17-jre
ARG NEW_RELIC_LICENSE_KEY
ENV NEW_RELIC_LICENSE_KEY=$NEW_RELIC_LICENSE_KEY

COPY --from=prep /opt/opentelemetry-jmx-scraper.jar /opt/opentelemetry-jmx-scraper.jar
COPY --from=prep /otelcol-contrib /otelcol-contrib

ENTRYPOINT ["/otelcol-contrib"]
CMD ["--config", "/conf/otel-agent-config.yaml"]
```

## Configuration

### Main Collector Config

Located at: `k8s/base/configs/otel-collector-kafka-config.yaml`

**Key receivers:**
```yaml
receivers:
  # JMX receiver for Kafka + JVM metrics
  jmx/kafka_broker-1:
    jar_path: /opt/opentelemetry-jmx-scraper.jar
    endpoint: service:jmx:rmi:///jndi/rmi://${env:KAFKA_BROKER_JMX_ADDRESS}/jmxrmi
    target_system: kafka                         # Built-in Kafka metrics
    jmx_configs: /conf/kafka-jmx-config.yaml    # Custom JVM metrics
    collection_interval: 30s

  # Kafka protocol metrics
  kafkametrics:
    brokers: ${env:KAFKA_BROKER_ADDRESS}
    protocol_version: 2.0.0
    scrapers: [brokers, topics, consumers]
```

### Custom JMX Metrics

Located at: `k8s/base/configs/kafka-jmx-config.yaml`

Defines custom JMX metrics including:
- **Garbage Collection:** Collection count and elapsed time per collector
- **Memory:** Heap usage, max, committed, and per-pool metrics
- **Threading:** Active thread count
- **CPU:** Process and system CPU utilization, load average
- **File Descriptors:** Open file descriptor count
- **Class Loading:** Loaded class count

### Internal Telemetry

Located at: `k8s/base/configs/internal-telemetry-config.yaml`

Monitors the collector itself:
- **Metrics Level:** `detailed` (most comprehensive)
- **Logs:** Sampled (first 10 per 10s, then 1 in 100)
- **Traces:** Disabled by default
- **Export:** Same New Relic endpoint as application metrics

Service identity:
- **Name:** `relibank-kafka-collector`
- **Type:** `otel_collector`
- **Version:** 0.145.0

## Deployment

### Kubernetes Deployment

Located at: `k8s/base/infrastructure/otel-collector-kafka-deployment.yaml`

**Environment variables:**
```yaml
env:
  # NEW_RELIC_LICENSE_KEY is baked into image at build time
  - name: KAFKA_CLUSTER_NAME
    value: "relibank-kafka"
  - name: KAFKA_BROKER_ADDRESS
    value: "kafka:29092"
  - name: KAFKA_BROKER_JMX_ADDRESS
    value: "kafka:9999"
  - name: INTERNAL_TELEMETRY_SERVICE_NAME
    value: "relibank-kafka-collector"
  - name: INTERNAL_TELEMETRY_OTLP_ENDPOINT
    value: "https://otlp.nr-data.net"
```

**ConfigMap volumes:**
- `otel-collector-kafka-config` → `/conf/otel-agent-config.yaml`
- `internal-telemetry-config` → `/conf/internal-telemetry-config.yaml`
- `kafka-jmx-config` → `/conf/kafka-jmx-config.yaml`

### Deploy with Skaffold

```bash
# Deploy to local Kubernetes
skaffold dev

# Deploy to production
skaffold run -p azure-prod
```

## Metrics Collected

### Kafka Metrics

**From JMX Receiver (target_system: kafka):**
- `kafka.server.total.fetch.requests` - Fetch request rate
- `kafka.server.total.produce.requests` - Produce request rate
- `kafka.server.log.flush.rate.and.time` - Log flush performance
- `kafka.network.request.total.time` - Network latency

**From Kafka Metrics Receiver:**
- `kafka.brokers` - Number of brokers
- `kafka.topic.partitions` - Partition count per topic
- `kafka.consumer_group.lag` - Consumer lag
- `kafka.partition.replicas_in_sync` - Replication health

**Cluster-level:**
- `kafka.cluster.partition.count` - Total partitions
- `kafka.cluster.topic.count` - Total topics
- `kafka.partition.offline` - Offline partitions (critical alert)
- `kafka.leader.election.rate` - Leader elections
- `kafka.broker.fenced.count` - Fenced brokers

### JVM Metrics

**From Custom JMX Config (kafka-jmx-config.yaml):**

**Garbage Collection:**
- `jvm.gc.collections.count` - GC events (by collector)
- `jvm.gc.collections.elapsed` - GC pause time (ms)

**Memory:**
- `jvm.memory.heap.used` / `max` / `committed`
- `jvm.memory.pool.used` - Per-pool (Eden, Survivor, Old Gen)

**Threading:**
- `jvm.thread.count` - Active threads (typical: 100-300)

**CPU & System:**
- `jvm.cpu.recent_utilization` - Process CPU (0.0-1.0)
- `jvm.system.cpu.utilization` - System CPU
- `jvm.system.cpu.load_1m` - 1-minute load average
- `jvm.file_descriptor.count` - Open file descriptors

### Internal Collector Metrics

**Receiver Health:**
- `otelcol_receiver_accepted_metric_points` - Metrics received
- `otelcol_receiver_refused_metric_points` - Rejected metrics

**Exporter Health:**
- `otelcol_exporter_sent_metric_points` - Successfully exported
- `otelcol_exporter_send_failed_metric_points` - Failed exports

**Resource Usage:**
- `otelcol_process_runtime_total_sys_memory_bytes` - Collector memory
- `otelcol_process_cpu_seconds` - Collector CPU

## Verification

### Check Pod Status
```bash
kubectl get pods -n relibank -l app=otel-collector-kafka
```

### Verify JMX Subprocess
```bash
# Should show Java process running JMX scraper
kubectl exec -n relibank deployment/otel-collector-kafka -- ps aux | grep java

# Expected output:
# root  19  X.X  0.2  ...  java io.opentelemetry.contrib.jmxscraper.JmxScraper -config /tmp/jmx-config-*.properties
```

### Check Logs
```bash
# Monitor logs for errors
kubectl logs -n relibank -l app=otel-collector-kafka -f

# Look for success message:
# "Everything is ready. Begin running and processing data."

# Check for errors (excluding harmless host.id warning)
kubectl logs -n relibank deployment/otel-collector-kafka | grep -i error | grep -v "failed to get host ID"
```

### Verify Configuration
```bash
# Check JMX config being used
kubectl exec -n relibank deployment/otel-collector-kafka -- cat /tmp/jmx-config-*.properties

# Verify environment variables
kubectl exec -n relibank deployment/otel-collector-kafka -- env | grep -E "KAFKA|NEW_RELIC|INTERNAL"
```

### Check Metrics in New Relic

Navigate to New Relic UI and run NRQL queries:

**Kafka metrics:**
```sql
FROM Metric
SELECT count(*)
WHERE metricName LIKE 'kafka.%'
AND kafka.cluster.name = 'relibank-kafka'
FACET metricName
SINCE 10 minutes ago
```

**JVM metrics:**
```sql
FROM Metric
SELECT latest(jvm.memory.heap.used) / latest(jvm.memory.heap.max) * 100 AS 'Heap Usage %',
       latest(jvm.thread.count) AS 'Thread Count'
WHERE kafka.cluster.name = 'relibank-kafka'
TIMESERIES
SINCE 30 minutes ago
```

**Collector health:**
```sql
FROM Metric
SELECT rate(sum(otelcol_receiver_accepted_metric_points), 1 minute) AS 'Metrics/min',
       rate(sum(otelcol_exporter_send_failed_metric_points), 1 minute) AS 'Failed/min'
WHERE service.name = 'relibank-kafka-collector'
TIMESERIES
SINCE 30 minutes ago
```

## Troubleshooting

### JMX Subprocess Not Starting

**Symptom:** Pod running but no Java process
```bash
kubectl exec -n relibank deployment/otel-collector-kafka -- ps aux | grep java
# No output
```

**Check logs:**
```bash
kubectl logs -n relibank -l app=otel-collector-kafka | grep -i "jmx\|error"
```

**Common causes:**
1. **Incorrect JMX endpoint format**
   - Must be: `service:jmx:rmi:///jndi/rmi://kafka:9999/jmxrmi`
   - Not just: `kafka:9999`

2. **Kafka JMX not exposed**
   - Verify Kafka has JMX enabled: `kubectl exec -n relibank deployment/kafka -- env | grep JMX`
   - Should see: `KAFKA_JMX_OPTS=-Dcom.sun.management.jmxremote...`

3. **Network connectivity**
   - Test from collector pod: `kubectl exec -n relibank deployment/otel-collector-kafka -- nc -zv kafka 9999`
   - Should return: `kafka (10.x.x.x:9999) open`

### 403 Forbidden Errors

**Symptom:** Logs show authentication failures
```
failed to send metrics to https://otlp.nr-data.net/v1/metrics: 403 Forbidden
```

**Causes:**
1. **Invalid license key** - Check the key in `skaffold.env`
2. **License key not baked into image** - Rebuild image with `skaffold dev` or `skaffold run`
3. **Wrong license key format** - Should be 40 hex chars (e.g., `b99ebb88e8c61bcebf539f29e183862bFFFFNRAL`)

**Verify license key:**
```bash
kubectl exec -n relibank deployment/otel-collector-kafka -- env | grep NEW_RELIC_LICENSE_KEY
```

### No Metrics in New Relic

**Check collector logs:**
```bash
kubectl logs -n relibank -l app=otel-collector-kafka --tail=100
```

**Verify export attempts:**
```bash
# Should see periodic log entries about metrics being sent
kubectl logs -n relibank -l app=otel-collector-kafka | grep -i "export\|sent"
```

**Check internal metrics endpoint:**
```bash
kubectl port-forward -n relibank svc/otel-collector-kafka 8888:8888
curl http://localhost:8888/metrics | grep otelcol_exporter_sent_metric_points
```

### High Memory Usage

**Check collector resource usage:**
```bash
kubectl top pod -n relibank -l app=otel-collector-kafka
```

**Tune batch processing:**
Edit `k8s/base/configs/otel-collector-kafka-config.yaml`:
```yaml
processors:
  batch/aggregation:
    send_batch_size: 512        # Reduce from 1024
    timeout: 15s                # Reduce from 30s
```

### host.id Warning (Safe to Ignore)

**Warning message:**
```
failed to get host ID ... error: empty "host.id"
```

**This is normal in Kubernetes** and doesn't affect functionality. The collector falls back to:
- `host.name`: Pod name (e.g., `otel-collector-kafka-xxx`)
- `service.instance.id`: UUID for uniqueness

To suppress (optional):
```yaml
processors:
  resourcedetection:
    detectors: [env, system]
    system:
      resource_attributes:
        host.id:
          enabled: false  # Disable host.id detection
```

## Production Readiness

### Required Changes

- [ ] **Resource Limits:** Add to deployment
  ```yaml
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"
  ```

- [ ] **TLS Configuration:** Enable TLS for OTLP export (when certs available)
- [ ] **Alerting Policies:** Configure in New Relic
  - Offline partitions > 0
  - Heap usage > 85%
  - File descriptors > 80% limit
  - Failed metric exports > 0

### Optional Enhancements

- [ ] Add liveness/readiness probes to deployment
- [ ] Enable collector traces for debugging (set INTERNAL_TELEMETRY_TRACE_LEVEL=basic)
- [ ] Create New Relic dashboards for Kafka + JVM metrics
- [ ] Tune collection intervals based on production load

## References

- [New Relic Kafka Self-Hosted Monitoring](https://docs.newrelic.com/docs/opentelemetry/integrations/kafka/self-hosted/)
- [OpenTelemetry JMX Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jmxreceiver)
- [OpenTelemetry JMX Scraper](https://github.com/open-telemetry/opentelemetry-java-contrib/tree/main/jmx-scraper)
- [OTel Collector Internal Telemetry](https://opentelemetry.io/docs/collector/internal-telemetry/)
- [Implementation History](../notes/otel-so-far.md) - Full evolution across 3 commits

## Related Files

- **Deployment:** `k8s/base/infrastructure/otel-collector-kafka-deployment.yaml`
- **Main Config:** `k8s/base/configs/otel-collector-kafka-config.yaml`
- **JMX Config:** `k8s/base/configs/kafka-jmx-config.yaml`
- **Internal Telemetry:** `k8s/base/configs/internal-telemetry-config.yaml`
- **Skaffold:** `skaffold.yaml` (build configuration)
- **Credentials:** `skaffold.env` (not in git, contains NEW_RELIC_LICENSE_KEY)

---

**Last Updated:** February 10, 2026
**Status:** ✅ Production-ready with verified metric export

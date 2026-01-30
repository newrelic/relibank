# Kafka Monitoring with OpenTelemetry

This setup implements New Relic's OpenTelemetry-based Kafka monitoring for the ReliBank Kafka cluster.

## Overview

The monitoring solution consists of:

1. **JMX enabled on Kafka broker** - Exposes Kafka metrics via JMX on port 9999
2. **OpenTelemetry Collector** - Separate deployment that collects metrics from Kafka
3. **JMX Scraper** - Collects detailed broker metrics via JMX
4. **Kafka Metrics Receiver** - Collects cluster-level metrics from Kafka brokers

## Architecture

```
Kafka Broker (port 9999 JMX)
         ↓
OpenTelemetry Collector
    ├─ JMX Receiver (broker metrics)
    └─ Kafka Metrics Receiver (cluster metrics)
         ↓
    New Relic OTLP Endpoint
```

## Components

### 1. Kafka Deployment
- **File**: `kafka-deployment.yaml`
- **Changes**:
  - Added JMX environment variables
  - Exposed port 9999 for JMX
  - Service updated to expose JMX port

### 2. OpenTelemetry Collector
- **File**: `otel-collector-kafka-deployment.yaml`
- **Image**: Custom built image with OTel Collector v0.144.0 and Java 17 runtime
- **JMX Support**: JMX scraper JAR (v1.52.0) bundled in the Docker image
- **Resources**:
  - Requests: 256Mi memory, 100m CPU
  - Limits: 512Mi memory, 500m CPU

### 3. ConfigMaps
- **File**: `../configs/otel-kafka-configmaps.yaml`
- **otel-collector-config**: Main collector configuration
- **kafka-jmx-config**: Custom JMX metric definitions

## Metrics Collected

### Broker Metrics (via JMX)
- Messages per second (per topic)
- Bytes in/out (per topic)
- Leader count per broker
- Under-replicated partitions
- JVM metrics (heap, GC, threads)
- CPU and file descriptor usage

### Cluster Metrics (via Kafka Receiver)
- Topic count
- Partition count
- Fenced brokers
- Preferred replica imbalance
- Consumer group lag
- Min ISR status

## Configuration

### Environment Variables

The OpenTelemetry Collector requires:

```yaml
NEW_RELIC_LICENSE_KEY: <from newrelic-secret>
KAFKA_CLUSTER_NAME: "relibank-kafka"
```

### OTLP Endpoint

Default: `https://otlp.nr-data.net:4317` (US region)

For EU region, update the collector config to use:
`https://otlp.eu01.nr-data.net:4317`

See: https://docs.newrelic.com/docs/opentelemetry/best-practices/opentelemetry-otlp/

## Deployment

### Prerequisites

1. Ensure the `newrelic-secret` exists in the `relibank` namespace:
   ```bash
   kubectl create secret generic newrelic-secret \
     --from-literal=license_key=<YOUR_LICENSE_KEY> \
     -n relibank
   ```

### Deploy

```bash
# From the k8s directory
kubectl apply -k base/

# Or using skaffold
skaffold dev
```

### Verify

Check the OpenTelemetry Collector logs:
```bash
kubectl logs -n relibank deployment/otel-collector-kafka -f
```

Check Kafka JMX port is accessible:
```bash
kubectl exec -n relibank deployment/kafka -- nc -zv kafka 9999
```

## Troubleshooting

### Collector fails to start
- Check if JMX scraper JAR is present in the image (`/opt/opentelemetry-jmx-scraper.jar`)
- Verify ConfigMaps are mounted correctly
- Ensure Java runtime is available in the container

### No metrics in New Relic
- Verify `NEW_RELIC_LICENSE_KEY` is set correctly
- Check collector logs for OTLP export errors
- Ensure network connectivity to New Relic OTLP endpoint

### JMX connection refused
- Verify Kafka pod has JMX environment variables set
- Check if port 9999 is exposed on Kafka service
- Verify hostname resolution (should be `kafka:9999`)

## Customization

### Add More Brokers

To monitor multiple Kafka brokers, add additional JMX receivers in the collector config:

```yaml
receivers:
  jmx/kafka_broker-2:
    endpoint: kafka-2:9999
    target_system: kafka,jvm
    collection_interval: 30s
    resource_attributes:
      broker.id: "2"
      broker.endpoint: kafka-2:9999
```

### Add Custom JMX Metrics

The JMX receiver uses the `target_system` parameter to determine which metrics to collect. Current setting is `kafka,jvm` which collects both Kafka and JVM metrics.

For advanced customization, see:
https://github.com/open-telemetry/opentelemetry-java-contrib/tree/main/jmx-metrics

### Change Collection Interval

Update `collection_interval` in both receivers (default: 30s):

```yaml
receivers:
  kafkametrics:
    collection_interval: 60s  # Reduce frequency
  jmx/kafka_broker-1:
    collection_interval: 60s
```

## References

- [New Relic Kafka OHI Documentation](https://docs.newrelic.com/docs/opentelemetry/integrations/kafka/self-hosted/)
- [OpenTelemetry Collector Documentation](https://opentelemetry.io/docs/collector/)
- [JMX Metrics Scraper](https://github.com/open-telemetry/opentelemetry-java-contrib/tree/main/jmx-metrics)
- [Kafka Metrics Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/kafkametricsreceiver)

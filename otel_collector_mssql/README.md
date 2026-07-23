# Relibank MSSQL OpenTelemetry Collector

Custom OpenTelemetry Collector for monitoring the Relibank MSSQL database with New Relic — built on New Relic's own NRDOT collector distro, using its SQL Server receiver plus host metrics and log tailing.

---

### 🚀 Key Features

* **SQL Server Metrics**: Uses the `newrelicsqlserver` receiver to collect instance, database, connection, wait-time, failover, security, lock, thread-pool, tempdb, and buffer metrics from `RelibankDB`.
* **Query Monitoring**: Fetches query-level and query-plan metrics on a 10s interval, converted into logs via the `metricsaslogs` connector.
* **Host Metrics**: Collects CPU/load/memory/paging/filesystem/disk/network metrics for the host running MSSQL.
* **Log Tailing**: Tails system logs (`syslog`, `auth`, `dpkg`, etc.) via the `filelog` receiver.
* **Self-Monitoring**: Reports its own internal telemetry to New Relic separately from application data.

---

### 📦 Interface

```
┌───────────────────────────┐
│  mssql-0 (RelibankDB)     │
│  :1433                    │
└─────────────┬─────────────┘
              │ newrelicsqlserver receiver (60s interval)
              ▼
┌─────────────────────────────────────────────┐
│  nrdot-collector-mssql                       │
│                                               │
│  Receivers:                                  │
│  ├─ newrelicsqlserver  (SQL Server metrics)  │
│  ├─ hostmetrics        (CPU/mem/disk/net)    │
│  ├─ filelog            (system logs)         │
│  └─ otlp               (grpc + http)         │
│                                               │
│  Connector:                                  │
│  └─ metricsaslogs (query-plan → logs)        │
│                                               │
│  Processors:                                 │
│  ├─ metricstransform, filter/*               │
│  ├─ cumulativetodelta, deltatorate           │
│  ├─ transform, transform/host                │
│  ├─ memory_limiter, batch                    │
│  └─ resourcedetection (+ cloud/env variants)  │
│                                               │
│  Exporters:                                  │
│  ├─ otlphttp (→ New Relic)                   │
│  └─ debug                                    │
└─────────────┬─────────────────────────────────┘
              │ OTLP/HTTP
              ▼
┌───────────────────────────┐
│  New Relic                │
│  (SQL Server dashboards,  │
│   alerts)                 │
└───────────────────────────┘
```

Pipelines: `metrics/host`, `traces`, `metrics` (SQL Server + otlp), `logs`, `metrics/exec_plan_to_logs`.

**What depends on it**: New Relic's SQL Server dashboards and any alert conditions built on MSSQL metrics depend on this collector staying up. It has no inbound Service/port — it's pull (scrape MSSQL) + push (export to New Relic) only, so nothing calls it directly.

---

### 🔧 Configuration

#### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MSSQL_NEWRELIC_PASSWORD` | — | Password for the `newrelic` SQL Server monitoring user (from Secret `nrdot-mssql-credentials`). |
| `NEW_RELIC_LICENSE_KEY` | — | New Relic ingest key for metrics/traces/logs export. |
| `NEW_RELIC_OTLP_ENDPOINT` | — | OTLP HTTP endpoint for application telemetry. |
| `INTERNAL_TELEMETRY_SERVICE_NAME` | `relibank-mssql-collector` | Service name used for the collector's own self-monitoring telemetry. |
| `INTERNAL_TELEMETRY_OTLP_ENDPOINT` | `https://otlp.nr-data.net` | Endpoint for the collector's internal telemetry. |
| `INTERNAL_TELEMETRY_NEW_RELIC_LICENSE_KEY` | — | License key for internal telemetry export. |
| `NEW_RELIC_MEMORY_LIMIT_MIB` | `256` | Optional cap for the `memory_limiter` processor. |

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and Kubernetes.

1. **Configure Environment**: Ensure `skaffold.env` (or the `nrdot-mssql-credentials` secret) contains `MSSQL_NEWRELIC_PASSWORD`, `NEW_RELIC_LICENSE_KEY`, and `NEW_RELIC_OTLP_ENDPOINT`.

2. **Start the Stack**: From the root of the `relibank` repository, run:

    ```bash
    skaffold dev
    ```

3. **Dependency**: Requires `mssql-0` to be reachable on port `1433` with a `newrelic` monitoring user provisioned on `RelibankDB`.

4. **Verify**: Check collector logs (`kubectl logs -n relibank deployment/nrdot-collector-mssql`) for successful export, or query New Relic for SQL Server metrics.

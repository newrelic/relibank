# Relibank Kafka Service

The Kafka broker that backs Relibank's event-driven, asynchronous communication between services. There is no custom application code here — this service packages and configures a single-node Kafka broker, exposing a JMX endpoint that `otel_collector_kafka` scrapes for monitoring.

---

### 🚀 Key Features

* **Single-Node Broker**: Runs Kafka as the shared message bus for payment, notification, and scheduling events across the stack.
* **Zookeeper-Coordinated**: Uses a separate `zookeeper` deployment for cluster coordination (Kafka 3.5, pre-KRaft).
* **JMX-Instrumented**: Exposes JMX on port `9999` (no auth/SSL) specifically so `otel_collector_kafka` can scrape broker and JVM metrics.
* **Dual Listeners**: Advertises a `PLAINTEXT` listener for in-cluster traffic and an `EXTERNAL` listener for local access from outside the cluster.

---

### 📦 Interface

Kafka itself has no REST surface — its interface is the set of topics services produce to and consume from it.

```
┌────────────────────┐        ┌──────────────────────────┐        ┌────────────────────────┐
│  bill_pay           │──────▶│                          │──────▶│  transaction_service    │
│  (producer)         │        │                          │        │  notifications_service  │
├────────────────────┤        │      kafka (broker)       │       └────────────────────────┘
│  scheduler_service   │──────▶│      :29092 (internal)   │
│  (producer)         │        │      :9092  (external)   │
├────────────────────┤        │      :9999  (JMX)         │──────▶  otel_collector_kafka
│  risk_assessment_    │──────▶│                          │        (JMX scrape, see its
│  service (producer) │        └──────────────────────────┘         own README)
└────────────────────┘                    ▲
                                            │ coordination
                                     ┌─────────────┐
                                     │  zookeeper   │
                                     │  :2181       │
                                     └─────────────┘
```

| Topic | Producer(s) | Consumer(s) |
| :--- | :--- | :--- |
| `bill_payments` | `bill_pay` | `notifications_service`, `transaction_service` |
| `bill_payments_declined` | `bill_pay` | `transaction_service` |
| `card_payments` | `bill_pay` | `transaction_service` |
| `card_payments_declined` | `bill_pay` | — |
| `recurring_payments` | `bill_pay` | `notifications_service` |
| `payment_cancellations` | `bill_pay` | — |
| `payment_due_notifications` | `scheduler_service` | `notifications_service` |
| `payment-declined` | `risk_assessment_service` | — |

Note: `payment-declined` uses a hyphen while every other topic uses underscores — an existing naming inconsistency, not something this README changes.

**What depends on it**: every service above depends on `kafka` being reachable (via the `KAFKA_BROKER` env var, default `kafka:29092`) for async event delivery; `otel_collector_kafka` depends on it for JMX metrics scraping.

---

### 🔧 Configuration

#### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ALLOW_PLAINTEXT_LISTENER` | `yes` | Allows unauthenticated plaintext connections (demo/local setup, not production-hardened). |
| `KAFKA_BROKER_ID` | `1` | Unique broker ID for this single-node cluster. |
| `KAFKA_CFG_ADVERTISED_LISTENERS` | `PLAINTEXT://kafka:29092,EXTERNAL://localhost:9092` | Addresses advertised to clients for each listener. |
| `KAFKA_CFG_LISTENERS` | `PLAINTEXT://:29092,EXTERNAL://:9092` | Listener bind addresses/ports. |
| `KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP` | `PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT` | Security protocol per listener name. |
| `KAFKA_CFG_ZOOKEEPER_CONNECT` | `zookeeper:2181` | Zookeeper coordination endpoint. |
| `KAFKA_JMX_OPTS` | JMX remote on port `9999`, no auth/SSL | Enables JMX so `otel_collector_kafka` can scrape broker/JVM metrics. |

Other services connect to this broker via their own `KAFKA_BROKER` env var, which defaults to `kafka:29092`.

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and Kubernetes.

1. **Configure Environment**: Ensure `skaffold.env` contains required variables.

2. **Start the Stack**: From the root of the `relibank` repository, run:

    ```bash
    skaffold dev
    ```

3. **Access**: In-cluster services connect via `kafka:29092`. From outside the cluster, the broker is reachable at `localhost:9092`. JMX metrics are exposed on `9999` and consumed by `otel_collector_kafka`, not accessed directly.

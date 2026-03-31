# Relibank Risk Assessment Service

This service is a core component of the **Relibank** FinServ application. Its primary function is to assess the risk of bill payment transactions before they are processed. It integrates with the **Support Service AI agent** for intelligent risk analysis and acts as a **producer** in our event-driven architecture, publishing risk assessment events to Kafka.

---

### =� Key Features

* **AI-Powered Risk Assessment**: Leverages Support Service AI agents to analyze transaction risk using advanced language models.

* **Event-Driven Architecture**: Publishes `payment-declined` events to Kafka when transactions are deemed risky.

* **RESTful API**: Exposes a RESTful API for risk assessment requests from Bill Pay service.

* **Comprehensive Logging**: Extensive structured logging with contextual information for observability.

* **eBPF Instrumentation**: Monitored via eBPF (not traditional APM), providing deep visibility without code instrumentation.

* **Service-to-Service Communication**: Makes synchronous API calls to the Support Service for AI-based risk analysis.

* **Asynchronous Event Publishing**: Publishes risk assessment results to Kafka for downstream consumption.

---

### =� API Endpoints

The service exposes the following API endpoints, designed to be consumed by the Bill Pay service.

#### Risk Assessment
| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/risk-assessment-service/assess-risk` | `POST` | Assesses transaction risk via Support Service AI agent. | `transaction_id`, `account_id`, `amount`, `payee`, `payment_method` |

#### Health Checks
| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/risk-assessment-service` | `GET` | Root endpoint that returns service status. | None |
| `/risk-assessment-service/health` | `GET` | Health check endpoint that returns `healthy` status. | None |
| `/risk-assessment-service/healthz` | `GET` | Kubernetes liveness probe endpoint. | None |

---

### = Architecture Flow

1. **Bill Pay** � Risk Assessment Service (before DB transaction)
2. **Risk Assessment** � Support Service AI Agent (risk analysis)
3. **Risk Assessment** � Kafka (publish `payment-declined` event if risky)
4. **Bill Pay** � Risk Assessment (receive decision)

---

### =� Risk Assessment Response

The service returns a comprehensive risk assessment:

```json
{
  "transaction_id": "txn_123",
  "decision": "approved",
  "risk_level": "low",
  "risk_score": 15.5,
  "reason": "Transaction appears legitimate based on account history",
  "assessment_duration_ms": 245
}
```

---

### =� Kafka Events

When a payment is declined, the service publishes an event to the `payment-declined` topic:

```json
{
  "transaction_id": "txn_123",
  "account_id": "acc_456",
  "amount": 1500.00,
  "payee": "Suspicious Vendor",
  "decision": "declined",
  "risk_level": "high",
  "risk_score": 85.0,
  "reason": "Unusual transaction pattern detected",
  "timestamp": "2026-03-30T20:15:30Z",
  "support_service_agent": "gpt-4",
  "assessment_duration_ms": 312
}
```

---

### > AI Agent Integration

The service calls the Support Service at `/support-service/assess-payment-risk` to leverage AI models for risk assessment. The Support Service can use different agents (e.g., GPT-4, GPT-3.5) which can be swapped at runtime for demo scenarios showing the impact of model changes.

**Agent Tracking**: The `support_service_agent` field in events and logs tracks which AI model made the risk decision, enabling visibility into model performance and impact.

---

### =� Observability

#### eBPF Instrumentation
This service is monitored via **eBPF** rather than traditional New Relic APM. eBPF provides:
- Distributed tracing without code instrumentation
- Network-level observability
- Low overhead monitoring

#### Logs in Context
Extensive structured logging with contextual fields:
- `transaction_id`: Links all logs for a transaction
- `account_id`: Customer account information
- `amount`: Transaction amount
- `risk_score`: Calculated risk score
- `risk_level`: Risk classification (low/medium/high)
- `decision`: Approval/decline decision
- `agent_used`: Which AI model made the decision
- `assessment_duration_ms`: Performance metrics

---

### � Configuration

#### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `KAFKA_BROKER` | `kafka:29092` | Kafka broker address |
| `SUPPORT_SERVICE_URL` | `http://support-service.relibank.svc.cluster.local:8000` | Support Service endpoint |

---

### � How to Run

This service is designed to be run using Skaffold as part of the larger **Relibank** application stack.

1.  **Configure Environment**: Ensure `skaffold.env` contains required variables.

2.  **Navigate to Root Directory**: Navigate to the root directory of the `relibank` repository.

3.  **Start the Stack**: Run the following command to build and deploy all services:

    ```bash
    skaffold dev
    ```

4.  **eBPF Setup**: Configure eBPF instrumentation on the cluster (requires cluster admin access).

---

### >� Testing

**Test risk assessment:**
```bash
curl -X POST http://localhost:5001/risk-assessment-service/assess-risk \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_test_123",
    "account_id": "acc_456",
    "amount": 100.00,
    "payee": "Test Vendor",
    "payment_method": "checking"
  }'
```

---

### 🚨 Rogue Deployment Demo

The Risk Assessment Service supports a "rogue deployment" scenario where the AI agent can be switched from balanced (gpt-4o) to extremely stringent (gpt-4o-mini) without code changes. This simulates a configuration change that causes the service to decline most payments.

**Architecture:**
- Risk Assessment Service → Support Service → Scenario Service
- Support Service queries Scenario Service for agent configuration on each request
- Scenario Service stores runtime configuration (toggled via API)

**Enable rogue agent** (gpt-4o-mini - declines most payments):
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/risk-assessment/rogue-agent?enabled=true"
```

**Disable rogue agent** (gpt-4o - normal balanced assessment):
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/risk-assessment/rogue-agent?enabled=false"
```

**Check current agent configuration:**
```bash
curl "http://localhost:8000/scenario-runner/api/risk-assessment/config"
```

**Agent Behavior:**

| Agent | Model | Behavior |
| :--- | :--- | :--- |
| **gpt-4o** (normal) | gpt-4o (2024-11-20) | Balanced risk assessment, approves legitimate transactions |
| **gpt-4o-mini** (rogue) | gpt-4.1-mini (2025-04-14) | Extremely stringent, declines transactions >$50, suspicious of unknown payees |

**Demo Workflow:**
1. Enable rogue agent via Scenario Service API
2. Send test payments through Bill Pay service
3. Watch New Relic for spike in declined transactions
4. Query `payment-declined` Kafka topic to see events
5. Check `support_service_agent` field in events to see which model made decisions
6. Disable rogue agent to restore normal behavior

**Expected Impact:**
- Normal (gpt-4o): ~5-10% decline rate for obviously risky transactions
- Rogue (gpt-4o-mini): ~90-95% decline rate for most transactions

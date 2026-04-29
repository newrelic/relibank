# Relibank

A microservices banking application built for chaos engineering and resilience testing.

## What is this?

Relibank simulates a banking system with separate services for accounts, transactions, bill payments, notifications, and scheduling. It's designed to help you learn about microservices resilience patterns and chaos engineering using Kubernetes and Chaos Mesh.

## Services

- **frontend-service** - React-based banking UI (React Router v7 + Material-UI)
  - Responsive design with mobile-first breakpoints
  - Bill payments, fund transfers, recurring payments
  - New Relic Browser monitoring integration
- **accounts-service** - Manages user accounts (FastAPI + PostgreSQL)
- **transaction-service** - Processes and retrieves payment transactions (FastAPI + MSSQL)
  - GET endpoint for recurring payment schedules
  - Kafka consumer for payment events
- **bill-pay-service** - Handles bill payments (FastAPI)
  - Integrates with risk-assessment-service for AI-powered payment fraud detection
- **risk-assessment-service** - AI-powered payment risk assessment (FastAPI)
  - Evaluates payment transactions before processing
  - Calls support-service AI agents for intelligent risk analysis
- **support-service** - Relibank's AI support service (FastAPI)
  - LangGraph-based support for customer support
  - Payment risk assessment using Azure OpenAI (gpt-4o/gpt-4o-mini)
- **notifications-service** - Sends notifications via Kafka
- **scheduler-service** - Schedules events via Kafka
- **Infrastructure:**
  - Kafka & Zookeeper - Message streaming
  - PostgreSQL - Accounts database
  - MSSQL - Transactions database
  - **otel-collector-kafka** - OpenTelemetry collector for Kafka monitoring
    - JMX metrics (Kafka broker + JVM telemetry)
    - Kafka protocol metrics
    - Internal collector telemetry
    - Exports to New Relic via OTLP
  - **nrdot-collector-mssql** - New Relic NRDOT collector for MSSQL database monitoring
    - Wait stats, performance counters, lock/deadlock metrics
    - Slow query and blocking query detection via `query_monitoring_*` config
    - Execution plan capture routed as logs via `metricsaslogs` connector
    - Exports to New Relic via OTLP (`instrumentation.provider = opentelemetry`)
- **scenario-runner-service** - Runtime configuration and chaos engineering control
    - Payment failure scenarios (timeout, decline, stolen card)
    - AI agent configuration for risk assessment (normal vs rogue agent)
    - Chaos Mesh experiment triggers
    - Locust load testing integration

## Getting Started

You'll need Docker Desktop with Kubernetes enabled (or Minikube), Skaffold, kubectl, and Helm installed.


### Credentials Setup

Add `MSSQL_NEWRELIC_PASSWORD` to your `skaffold.env` (it's already in the New Relic section):

```bash
# In skaffold.env, under # New Relic:
MSSQL_NEWRELIC_PASSWORD=YourStrong@Password!
```

A pre-deploy hook in `skaffold.yaml` automatically generates `k8s/base/infrastructure/newrelic/nrdot-mssql.env` from `skaffold.env` before every deploy — no separate file to maintain. See `nrdot-mssql.env.example` for the full variable mapping.

For CI/CD (GitHub Actions), add `MSSQL_NEWRELIC_PASSWORD` to the `events` environment secrets — the workflow already includes it in the `skaffold.env` creation step.

### Deploy Everything
Note - all secrets and configs are managed under `k8s/base/configs/*`

```bash
# Deploy to local Kubernetes
skaffold dev
```

This will:
- Build and deploy all service images
- Deploy the microservices to Kubernetes
- Install Chaos Mesh for chaos engineering
- Set up port forwarding so you can access the services

### Access the Services

Once deployed, you can access:
- **Frontend UI**: http://localhost:3000 (Main banking interface)
- Accounts: http://localhost:5002
- Auth Service: http://localhost:5006
- Transactions: http://localhost:5001
- Bill Pay: http://localhost:5000
- Support Service: http://localhost:5003
- Scheduler: http://localhost:5004
- Scenario Runner: http://localhost:8000
- Chaos Mesh Dashboard: http://localhost:2333

## Environment-Specific Deployments

The project uses Kustomize overlays for different environments:

**Local Development:**
- Uses Minikube's built-in "standard" storage class
- Deploys with `skaffold dev`

**Azure Staging:**  
- Uses "azure-disk" storage class for AKS
- Deploys with `skaffold dev -p staging`

## Chaos Engineering

Chaos Mesh gets installed automatically and includes pre-built experiments in `chaos_mesh/experiments/`. 

Access the dashboard at http://localhost:2333, or on the scenario page at http://localhost:8000 to:
- Kill random pods
- Inject network latency
- Stress CPU/memory
- Simulate database failures

Or deploy experiments manually:
```bash
kubectl apply -f chaos_mesh/experiments/relibank-pod-chaos-examples.yaml
```

## Development Tips

**View logs:**
```bash
kubectl logs -f deployment/accounts-service -n relibank
```

**Connect to databases:**
```bash
# PostgreSQL
kubectl exec -it deployment/accounts-db -n relibank -- psql -U postgres -d accountsdb

# MSSQL  
kubectl exec -it statefulset/mssql -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -C
```

**Check what's running:**
```bash
kubectl get pods -n relibank
```

## API Examples

The services expose REST APIs. Some examples:

**Create an account:**
```bash
curl -X POST http://localhost:5002/accounts \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

**Make a transaction:**
```bash  
curl -X POST http://localhost:5001/transactions \
  -H "Content-Type: application/json" \
  -d '{"from_account": 1, "to_account": 2, "amount": 100.00}'
```

## Troubleshooting

**Services won't start?** Check that your environment variables are set correctly and you've sourced the `skaffold.env` file.

**Database connection issues?** Make sure the database pods are running and healthy. The init jobs need to complete successfully.

**Storage issues?** If you're on Minikube, make sure it has the "standard" storage class. On AKS, make sure you have the "azure-disk" storage class.

## What's the Point?

This isn't meant to be a real banking application. It's a learning tool for:
- Microservices architecture patterns
- Kubernetes deployment strategies
- Chaos engineering practices
- Service mesh concepts
- Observability and monitoring with New Relic
- Responsive web application design

## Recent Updates

### NRDOT MSSQL Database Monitoring
- **NRDOT Collector**: Dedicated `nrdot-collector-mssql` pod running New Relic's NRDOT collector v1.11.1+db-v1.2.0
- **Wait Stats & Perf Counters**: `sqlserver.wait_stats.*`, lock/deadlock/compilation rates from `sys.dm_os_wait_stats` and `sys.dm_os_performance_counters`
- **Slow & Blocking Queries**: Captured via `query_monitoring_*` receiver config and routed as logs through the `metricsaslogs` connector
- **Credentials**: Managed via `k8s/base/infrastructure/newrelic/nrdot-mssql.env` (gitignored); see `nrdot-mssql.env.example`
- **GitHub Actions**: `MSSQL_NEWRELIC_PASSWORD` and `NR_LICENSE_KEY` secrets are used to generate the credentials file at deploy time

### Stripe Per-User Credentials
- **Seeded Stripe Data**: All 43 seeded users now have pre-populated `stripe_customer_id`, `stripe_payment_method_id`, and `stripe_payment_method_name` in Postgres
- **Dynamic Credential Resolution**: Bill Pay service resolves Stripe credentials dynamically via accounts-service lookup — pass `userId` to `/card-payment` instead of a hardcoded customer ID
- **Frontend Login Fetch**: Frontend fetches each user's Stripe customer ID from accounts-service at login, eliminating hardcoded IDs
- **New Endpoint**: `GET /accounts-service/users/by-id/{user_id}` — look up a user and their Stripe credentials by numeric ID
### AI-Powered Payment Risk Assessment
- **Risk Assessment Service**: All bill payments (bank and card) go through AI-powered risk assessment before processing
- **Support Service Integration**: Uses Azure OpenAI (gpt-4o for normal, gpt-4o-mini for rogue scenarios)
- **Scenario-Based Control**: Runtime agent swapping via Scenario Service for demo purposes
- **Rogue Agent Demo**: Toggle to gpt-4o-mini agent that declines 90%+ of payments to simulate misconfigured AI
- **Full Audit Trail**: Declined payments recorded in transaction database with risk level and reasoning
- **Kafka Integration**: Declined payments published to `bill_payments_declined` topic for downstream processing
- **Testing**: Comprehensive test suite in `tests/test_rogue_deployment_scenarios.py`

### New Relic User ID Tracking
- **Browser User Tracking**: Automatic user ID assignment for New Relic Browser sessions
  - Random user selection from database or header-based override via `x-browser-user-id`
  - Persistent across page navigation using sessionStorage
  - New endpoint: `/accounts-service/browser-user`
- **APM User Tracking**: Comprehensive user ID tracking across all backend services
  - Automatic extraction of `x-browser-user-id` header in all services
  - Header propagation through inter-service HTTP calls
  - Unified user tracking from browser → frontend → backend services
- **Testing**: Full test coverage for browser and APM user tracking scenarios

### UI Enhancements
- **Responsive Design**: Mobile-first breakpoints (xs/sm/md/lg/xl) across all pages
- **Simplified Bill Pay**: Unified payment method dropdown for easier UX
- **Default Transfer Amount**: Pre-filled $5.00 for faster demos
- **Updated Branding**: Larger logo (64x64px) in sidebar with primary green color
- **Favicon**: Added ReliBank logo as browser favicon
- **Payment Methods Scrolling**: Fixed height with vertical scrolling on desktop

### Backend Enhancements
- **Recurring Payments Endpoint**: GET `/transaction-service/recurring-payments` to fetch recurring payment schedules from database
- **Date Conversion**: Automatic MSSQL date-to-string conversion for proper JSON serialization
- **Active Schedule Filtering**: Frontend filters cancelled vs active recurring payments

### Infrastructure Monitoring
- **Kafka OpenTelemetry Collector**: Comprehensive monitoring of Kafka infrastructure
  - **JMX Metrics**: Kafka broker metrics via JMX (topics, partitions, replication, leader elections)
  - **JVM Telemetry**: Full JVM observability (GC, memory, threads, CPU, file descriptors)
  - **Kafka Protocol Metrics**: Native Kafka metrics (broker count, consumer lag, partition health)
  - **Internal Telemetry**: Collector self-monitoring with detailed metrics
  - **Export to New Relic**: All metrics sent to New Relic via OTLP
  - See [`otel_collector_kafka/README.md`](otel_collector_kafka/README.md) for details

Try breaking things with Chaos Mesh and see how the system responds!

---

### ⚙️ Test connection to New Relic

1. Connect to the service's container, docker example `docker exec -it bill-pay /bin/sh`

2. newrelic-admin validate-config LOCATION_OF_NEWRELIC.INI

3. If needed, add a logfile to newrelic.ini
```[newrelic]
log_file = /app/newrelic.log
log_level = info
```

4. Validate logs with ```docker exec -it bill-pay cat newrelic-agent.log```

---

### ⚙️ Formatting

1. ```ruff format``` https://docs.astral.sh/ruff/formatter/#ruff-format 

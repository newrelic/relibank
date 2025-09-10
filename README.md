# Relibank

A microservices banking application built for chaos engineering and resilience testing.

## What is this?

Relibank simulates a banking system with separate services for accounts, transactions, bill payments, notifications, and scheduling. It's designed to help you learn about microservices resilience patterns and chaos engineering using Kubernetes and Chaos Mesh.

## Services

- **accounts-service** - Manages user accounts (FastAPI + PostgreSQL)
- **transaction-service** - Processes payments (FastAPI + MSSQL)  
- **bill-pay-service** - Handles bill payments (FastAPI)
- **notifications-service** - Sends notifications via Kafka
- **scheduler-service** - Schedules events via Kafka
- **Infrastructure** - Kafka, Zookeeper, databases

## Getting Started

You'll need Docker Desktop with Kubernetes enabled (or Minikube), Skaffold, kubectl, and Helm installed.


### Deploy Everything
Note - all secrets and configs are managed under `k8s/base/configs/*`

```bash
# Deploy to local Kubernetes
skaffold dev
```

This will:
- Build all the Docker images
- Deploy the microservices to Kubernetes
- Install Chaos Mesh for chaos engineering
- Set up port forwarding so you can access the services

### Access the Services

Once deployed, you can access:
- Accounts: http://localhost:5002
- Transactions: http://localhost:5001  
- Bill Pay: http://localhost:5000
- Chatbot: http://localhost:5003
- Scheduler: http://localhost:5004
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

Access the dashboard at http://localhost:2333 to:
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
- Observability and monitoring

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

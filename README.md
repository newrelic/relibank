# Relibank - Microservices Banking Application

A resilient microservices banking application with chaos engineering capabilities using Kubernetes, Skaffold, and Chaos Mesh.

## 🏗️ Architecture

- **Accounts Service** - User account management (Python/Flask + PostgreSQL)
- **Transaction Service** - Payment processing (Python/FastAPI + MSSQL)
- **Bill Pay Service** - Bill payment processing (Python/Flask)
- **Notifications Service** - Event notifications (Python + Kafka)
- **Scheduler Service** - Event scheduling (Python + Kafka)
- **Infrastructure** - Kafka, Zookeeper, PostgreSQL, MSSQL

## 🚀 Quick Start

### Prerequisites

- Docker Desktop with Kubernetes enabled
- [Skaffold](https://skaffold.dev/docs/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)

### Deploy to Kubernetes

```bash
# Deploy everything (services + chaos mesh + ingress)
./deploy-k8s.sh

# Add DNS entries to /etc/hosts for local access:
echo "127.0.0.1 relibank.local" | sudo tee -a /etc/hosts
echo "127.0.0.1 chaos.relibank.local" | sudo tee -a /etc/hosts
```

### Web Access (Multi-User Demo)

Once deployed, the application is accessible via web browser:

🏦 **Relibank Services:**
- Accounts: `http://relibank.local:8080/accounts`
- Transactions: `http://relibank.local:8080/transactions`
- Bill Pay: `http://relibank.local:8080/billpay`

🔬 **Chaos Mesh Dashboard:** `http://chaos.relibank.local:8080`

📊 **Alternative localhost access:**
- Chaos Dashboard: `http://localhost:8080/chaos`
- Services: `http://localhost:8080/accounts`, `/transactions`, `/billpay`

### Development with Skaffold

```bash
# Start development mode (auto-rebuild on changes)
skaffold dev --profile=local

# Deploy without development mode
skaffold run --profile=local

# Clean up
./cleanup-k8s.sh
```

## 🔬 Chaos Engineering

The system includes automated chaos experiments powered by Chaos Mesh:

### Active Experiments

- **Pod Chaos**: Randomly kills application pods every 5 minutes
- **Database Failures**: Simulates database outages every 10 minutes  
- **Network Delays**: Adds latency to service communications
- **CPU Stress**: Tests performance under load
- **Network Partitions**: Isolates services to test resilience

### Managing Chaos Experiments

```bash
# View active experiments
kubectl get chaos -n relibank

# Stop specific experiment
kubectl delete podchaos relibank-pod-kill -n relibank

# Stop all experiments
kubectl delete chaos --all -n relibank

# Re-apply experiments
kubectl apply -f chaos_mesh/experiments/
```

### Custom Chaos Experiments

Edit files in `chaos-mesh/experiments/` to customize:
- Target different services
- Adjust failure frequencies
- Modify impact severity
- Add new experiment types

## 📊 Monitoring

```bash
# Watch pod status during chaos
kubectl get pods -n relibank -w

# View service logs
kubectl logs -f deployment/accounts-service -n relibank
kubectl logs -f deployment/transaction-service -n relibank

# Check experiment status
kubectl describe podchaos relibank-pod-kill -n relibank

# View ingress status
kubectl get ingress --all-namespaces
```

## 🏠 Local Development (Docker Compose)

For local development without Kubernetes:

```bash
# Start services
docker-compose up -d

# Simple chaos commands
./simple-chaos.sh kill      # Kill random container
./simple-chaos.sh restart   # Restart random container
./simple-chaos.sh pause     # Pause container
```

## 🗂️ Project Structure

```
relibank/
├── skaffold.yaml                    # Skaffold configuration
├── deploy-k8s.sh                   # Kubernetes deployment
├── cleanup-k8s.sh                  # Cleanup script
├── k8s/                            # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── infrastructure/kafka.yaml
│   ├── databases/databases.yaml
│   └── services/relibank-services.yaml
├── chaos-mesh/experiments/         # Chaos experiments
│   ├── pod-kill-experiment.yaml
│   ├── network-delay-experiment.yaml
│   └── stress-chaos-experiment.yaml
├── accounts_service/               # Account management
├── transaction_service/            # Payment processing
├── bill_pay/                       # Bill payments
├── notifications_service/          # Notifications
└── event_scheduler/                # Event scheduling
```

## 🎯 Testing Resilience

The chaos experiments automatically test:

1. **Service Recovery** - Pods are killed and should auto-restart
2. **Database Resilience** - Database failures test connection handling
3. **Network Tolerance** - Latency and partitions test timeout handling
4. **Performance Under Load** - CPU stress tests resource management
5. **Inter-service Communication** - Network chaos tests retry logic

## 🛠️ Configuration

### Environment Variables

Services use ConfigMaps and Secrets for configuration:
- Database credentials in `k8s/secrets.yaml`
- Service URLs in `k8s/configmap.yaml`
- Kafka brokers and endpoints

### Scaling

```bash
# Scale application services
kubectl scale deployment accounts-service --replicas=3 -n relibank
kubectl scale deployment transaction-service --replicas=3 -n relibank

# Scale with Skaffold
# Edit replica counts in k8s/services/relibank-services.yaml
```

## 🔧 Troubleshooting

### Common Issues

1. **Pods not starting**: Check resource limits and dependencies
2. **Database connections failing**: Verify secrets and network policies
3. **Chaos experiments not working**: Ensure Chaos Mesh is properly installed

### Debug Commands

```bash
# Check pod status
kubectl describe pod <pod-name> -n relibank

# View recent events
kubectl get events -n relibank --sort-by='.metadata.creationTimestamp'

# Check resource usage
kubectl top pods -n relibank
```

## 📈 Production Considerations

- Adjust resource requests/limits in service manifests
- Configure persistent storage for databases
- Set up monitoring with Prometheus/Grafana
- Implement proper RBAC for Chaos Mesh
- Use GitOps for experiment management

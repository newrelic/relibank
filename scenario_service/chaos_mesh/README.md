# Chaos Mesh Experiments for Relibank

This directory contains Chaos Mesh experiments for testing the resilience of the Relibank microservices in Kubernetes.

## 🎯 Experiments

The experiments are automatically applied when deploying with Skaffold and can be triggered manually from the Relibank Scenario Runner dashboard.

### Pod Chaos Experiments (relibank-pod-chaos-adhoc.yaml)

Your setup includes 5 scheduled pod chaos experiments targeting critical Relibank services:

1. **Payment Flow Pod Chaos** (`relibank-payment-flow-pod-chaos-schedule`)
   - Targets: `transaction-service` 
   - Action: Pod kill for 2 minutes
   - Schedule: Sunday 2:00 AM

2. **Database Connection Pod Chaos** (`relibank-database-connection-pod-chaos-schedule`)
   - Targets: `accounts-service`
   - Action: Pod failure for 90 seconds  
   - Schedule: Sunday 2:15 AM

3. **Messaging Service Pod Chaos** (`relibank-messaging-service-pod-chaos-schedule`)
   - Targets: `notifications-service`
   - Action: Pod kill for 60 seconds
   - Schedule: Sunday 2:30 AM

4. **Bill Pay Resilience Test** (`relibank-bill-pay-resilience-test-schedule`)
   - Targets: `bill-pay-service`
   - Action: Pod failure for 2 minutes
   - Schedule: Sunday 2:45 AM

5. **Scheduler Service Chaos** (`relibank-scheduler-service-chaos-schedule`)
   - Targets: `scheduler-service`
   - Action: Pod kill for 45 seconds
   - Schedule: Sunday 3:00 AM

### Stress Chaos Experiments (relibank-stress-scenarios.yaml)

Stress testing experiments inject CPU, memory, and I/O stress into services to validate performance under load:

1. **CPU Stress Test** (`relibank-cpu-stress-test`)
   - Targets: `transaction-service`
   - Stress: 50% CPU load with 2 workers
   - Duration: 2 minutes

2. **High CPU Stress** (`relibank-high-cpu-stress`)
   - Targets: `transaction-service`
   - Stress: 95% CPU load with 4 workers
   - Duration: 2 minutes

3. **Memory Stress Test** (`relibank-memory-stress-test`)
   - Targets: `bill-pay-service`
   - Stress: 256MB memory allocation with 2 workers
   - Duration: 2 minutes

4. **High Memory Stress** (`relibank-high-memory-stress`)
   - Targets: `bill-pay-service`
   - Stress: 512MB memory allocation with 4 workers
   - Duration: 2 minutes

5. **Combined Stress Test** (`relibank-combined-stress-test`)
   - Targets: `transaction-service`
   - Stress: 50% CPU + 256MB memory (2 workers each)
   - Duration: 2 minutes

**Note**: Stress scenarios require containerd as the container runtime. They may not work on Docker Desktop which uses the Docker runtime. Use containerd-based environments (Minikube, Kind, AKS, EKS) for stress testing.

## 🚀 Usage

Experiments are automatically deployed with the main application:

```bash
# Deploy everything including chaos experiments
skaffold dev

# View all scheduled experiments
kubectl get schedules -n relibank

# Manually trigger an experiment from dashboard or CLI
kubectl create job --from=schedule/relibank-payment-flow-pod-chaos-schedule manual-test-$(date +%s) -n relibank
```

## 🌐 Dashboard Access

The Chaos Mesh dashboard is accessible at:
- **Local Development**: http://localhost:2333
- **Features**: 
  - View scheduled experiments
  - Manually trigger experiments
  - Monitor experiment status and history
  - Real-time chaos experiment management

## 📊 Managing Experiments

```bash
# View active scheduled experiments
kubectl get schedules -n relibank

# View experiment history
kubectl get jobs -n relibank

# Apply specific experiment manually
kubectl apply -f chaos_mesh/experiments/relibank-pod-chaos-adhoc.yaml
kubectl apply -f chaos_mesh/experiments/relibank-stress-scenarios.yaml

# Stop a running experiment
kubectl delete podchaos <experiment-name> -n relibank
kubectl delete stresschaos <experiment-name> -n relibank

# View experiment details in dashboard or CLI
kubectl describe schedule relibank-payment-flow-pod-chaos-schedule -n relibank
```

## 🔧 Customizing Experiments

Edit experiment YAML files to customize:
- **Target services**: Modify `labelSelectors` under `selector` (currently targeting `app: service-name`)
- **Stress levels**: Adjust CPU load percentage, memory size, or worker counts
- **Duration**: Change how long experiments run
- **Chaos actions**: For pod chaos, choose between pod-kill or pod-failure

All experiments target pods with matching service labels in the `relibank` namespace.

## 🛡️ Rate Limiting

To prevent abuse, chaos experiments have rate limiting enabled:
- **Cooldown period**: 1 minute locally, 5 minutes in production
- **Concurrent limit**: Maximum 3 chaos experiments running simultaneously
- **Applies to**: Both pod chaos and stress chaos experiments

Check rate limit status via Scenario Runner API:
```bash
curl http://localhost:8000/scenario-runner/api/chaos-rate-limit-status
```

## 🎭 Features

- **Scheduled Execution** - Experiments run automatically every Sunday morning
- **Staggered Timing** - 15-minute intervals prevent overlap
- **Manual Triggering** - Use dashboard to run experiments on-demand
- **Safe Targeting** - Only affects services with specific labels
- **Web Dashboard** - No terminal access required for basic operations

# Chaos Mesh Experiments for Relibank

This directory contains Chaos Mesh experiments for testing the resilience of the Relibank microservices in Kubernetes.

## 🎯 Experiments

The experiments are automatically applied when deploying with Skaffold and can be triggered manually from the dashboard:

### Pod Chaos Experiments (relibank-pod-chaos-examples.yaml)

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
kubectl apply -f chaos_mesh/experiments/relibank-pod-chaos-examples.yaml

# Stop a running experiment
kubectl delete job <job-name> -n relibank

# View experiment details in dashboard or CLI
kubectl describe schedule relibank-payment-flow-pod-chaos-schedule -n relibank
```

## 🔧 Customizing Experiments

Edit `relibank-pod-chaos-examples.yaml` to:
- Change target services using `labelSelectors` (currently targeting `io.kompose.service`)
- Adjust schedule timing with cron expressions (currently Sunday early morning)
- Modify chaos actions (pod-kill vs pod-failure)
- Change experiment duration
- Add new experiments to the file

All experiments target pods with matching service labels in the `relibank` namespace.

## 🎭 Features

- **Scheduled Execution** - Experiments run automatically every Sunday morning
- **Staggered Timing** - 15-minute intervals prevent overlap
- **Manual Triggering** - Use dashboard to run experiments on-demand
- **Safe Targeting** - Only affects services with specific labels
- **Web Dashboard** - No terminal access required for basic operations

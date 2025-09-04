# Chaos Mesh Experiments for Relibank

This directory contains Chaos Mesh experiments for testing the resilience of the Relibank microservices in Kubernetes.

## 🎯 Experiments

The experiments in this directory are automatically applied when deploying with Skaffold:

### 1. Pod Chaos Experiments
- `pod-kill-experiment.yaml` - Randomly kills application and database pods to test recovery

### 2. Network Chaos Experiments  
- `network-delay-experiment.yaml` - Introduces network latency between services
- `network-partition-experiment.yaml` - Simulates network partitions between services
- `network-loss-experiment.yaml` - Simulates packet loss

### 3. Stress Testing
- `stress-chaos-experiment.yaml` - CPU and memory stress testing

### 4. Database and Infrastructure Testing
- `database-failure-experiment.yaml` - Tests database connectivity issues
- `kafka-chaos-experiment.yaml` - Tests message queue resilience
- `io-chaos-experiment.yaml` - Simulates disk I/O issues

### 5. Comprehensive Workflows
- `comprehensive-workflow.yaml` - Complex multi-stage chaos scenarios

## 🚀 Usage

Experiments are automatically deployed with the main application:

```bash
# Deploy everything including chaos experiments
./deploy-k8s.sh

# Or use Skaffold directly
skaffold run --profile=local
```

## 🌐 Multi-User Dashboard Access

The Chaos Mesh dashboard is accessible via web browser (no port-forwarding needed):

**Primary Access:**
- `http://chaos.relibank.local:8080` (requires /etc/hosts entry)

**Alternative Access:**
- `http://localhost:8080/chaos`

To set up DNS entries:
```bash
echo "127.0.0.1 chaos.relibank.local" | sudo tee -a /etc/hosts
```

## 📊 Managing Experiments

```bash
# View active experiments
kubectl get chaos -n relibank

# Apply specific experiment
kubectl apply -f chaos_mesh/experiments/pod-kill-experiment.yaml

# Stop all experiments
kubectl delete chaos --all -n relibank

# View experiment details in dashboard or CLI
kubectl describe podchaos relibank-pod-kill -n relibank
```

## 🔧 Customizing Experiments

Edit the YAML files to:
- Change target services using label selectors
- Adjust failure frequencies with cron schedules  
- Modify impact severity (duration, intensity)
- Add new experiment types

All experiments target pods with the `chaos-mesh.org/inject: enabled` label in the `relibank` namespace.

## 🎭 Demo Features

For multi-user demos, the setup includes:
- **Web-accessible dashboard** - No terminal access required
- **Automated experiments** - Chaos runs continuously  
- **Visual monitoring** - Real-time experiment status
- **Easy experiment control** - Start/stop via web UI

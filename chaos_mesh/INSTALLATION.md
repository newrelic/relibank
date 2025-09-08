# Chaos Mesh Installation Guide for Relibank

## 🚀 Automated Installation (Recommended)

Chaos Mesh is automatically installed via Skaffold:

```bash
# Deploy everything including Chaos Mesh
skaffold dev

# View deployment status
kubectl get pods -n chaos-mesh
```

This will:
1. ✅ Install Chaos Mesh v2.6.2 via Helm
2. ✅ Create `chaos-mesh` namespace automatically  
3. ✅ Label `relibank` namespace for chaos injection
4. ✅ Deploy 5 scheduled chaos experiments
5. ✅ Set up port forwarding for dashboard access at localhost:2333

## 🌐 Dashboard Access

After deployment, access the Chaos Mesh dashboard at:
- **Local Development**: http://localhost:2333
- **Features**: Web UI for viewing/managing scheduled chaos experiments
- **No Authentication**: Configured for easy local development

## 🎯 Ready for Chaos Experiments

Your Relibank namespace is automatically labeled with `chaos-mesh.org/inject=enabled`, and 5 scheduled experiments are deployed:

```bash
# View scheduled experiments
kubectl get schedules -n relibank

# Deploy experiments manually (already done by Skaffold)
kubectl apply -f chaos_mesh/experiments/relibank-pod-chaos-examples.yaml

# View active chaos jobs
kubectl get jobs -n relibank | grep chaos
```

## 🔧 Manual Installation (Alternative)

If you prefer manual installation:

```bash
# Add repository
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# Install with custom values
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace=chaos-mesh \
  --create-namespace \
  --values chaos_mesh/values.yaml \
  --version 2.6.2

# Enable chaos injection
kubectl label namespace relibank chaos-mesh.org/inject=enabled

# Deploy experiments
kubectl apply -f chaos_mesh/experiments/relibank-pod-chaos-examples.yaml
```

## 🕒 Experiment Schedule

All experiments are scheduled to run automatically:
- **Sunday 2:00 AM** - Payment flow pod chaos (transaction-service)
- **Sunday 2:15 AM** - Database connection chaos (accounts-service)  
- **Sunday 2:30 AM** - Messaging service chaos (notifications-service)
- **Sunday 2:45 AM** - Bill pay resilience test (bill-pay-service)
- **Sunday 3:00 AM** - Scheduler service chaos (scheduler-service)

Or trigger manually from the dashboard at localhost:2333.

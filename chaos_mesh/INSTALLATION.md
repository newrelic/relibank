# Chaos Mesh Installation Guide for Relibank

## 🚀 Automated Installation (Recommended)

Chaos Mesh is now automatically installed via Skaffold:

```bash
# Deploy everything including Chaos Mesh
skaffold dev --profile local

# Or for one-time deployment
skaffold run --profile local
```

This will:
1. ✅ Install Chaos Mesh v2.6.2 via Helm
2. ✅ Create `chaos-mesh` namespace automatically  
3. ✅ Label `relibank` namespace for chaos injection
4. ✅ Set up port forwarding for dashboard access

## 🌐 Dashboard Access

After deployment, access the Chaos Mesh dashboard at:
- **Local Development**: http://localhost:2333
- **Features**: Web UI for creating/managing chaos experiments
- **No Authentication**: Configured for easy local development

## 🎯 Ready for Chaos Experiments

Your Relibank namespace is automatically labeled with `chaos-mesh.org/inject=enabled`, so you can immediately deploy chaos experiments:

```bash
# Deploy individual experiments
kubectl apply -f chaos_mesh/experiments/pod-kill-experiment.yaml

# Deploy all experiments
kubectl apply -f chaos_mesh/experiments/

# View active experiments
kubectl get chaos -n relibank
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
```

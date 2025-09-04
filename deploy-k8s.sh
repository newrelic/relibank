#!/bin/bash

# Kubernetes deployment script for Relibank with Chaos Mesh
set -e

echo "🚀 Deploying Relibank to Kubernetes with Chaos Mesh for multi-user access..."

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

if ! command -v skaffold &> /dev/null; then
    echo "❌ Skaffold is not installed. Please install Skaffold first."
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo "❌ Helm is not installed. Please install Helm first."
    exit 1
fi

if ! command -v minikube &> /dev/null; then
    echo "❌ Minikube is not installed. Please install minikube first."
    exit 1
fi

# Ensure minikube is running
if ! minikube status | grep -q "Running"; then
    echo "🔄 Starting minikube..."
    minikube start --driver=docker --cpus=4 --memory=8192
fi

# Enable ingress addon for minikube
echo "🔌 Enabling minikube ingress addon..."
minikube addons enable ingress

# Ensure we're connected to minikube
kubectl config use-context minikube

echo "✅ Prerequisites check passed"

# Clean up any previous deployments
echo "🧹 Cleaning up previous deployments..."
helm uninstall chaos_mesh -n chaos-system --ignore-not-found
helm uninstall ingress-nginx -n ingress-nginx --ignore-not-found
kubectl delete namespace relibank --ignore-not-found=true

# Deploy using Skaffold
echo "🏗️  Building and deploying Relibank services with Skaffold..."
skaffold run --profile=local

echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=300s
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=chaos_mesh -n chaos-system --timeout=300s
kubectl wait --for=condition=Ready pods -l tier=infrastructure -n relibank --timeout=300s
kubectl wait --for=condition=Ready pods -l tier=database -n relibank --timeout=300s
kubectl wait --for=condition=Ready pods -l tier=application -n relibank --timeout=300s

# Get minikube IP for access
MINIKUBE_IP=$(minikube ip)

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access URLs:"
echo "🔬 Chaos Mesh Dashboard: http://localhost:2333 (port-forwarded)"
echo "🏦 Relibank Services (port-forwarded):"
echo "   • Accounts: http://localhost:5002"
echo "   • Transactions: http://localhost:5001"
echo "   • Bill Pay: http://localhost:5000"
echo ""
echo "🌍 Alternative access via minikube IP ($MINIKUBE_IP):"
echo "   • Via ingress: http://$MINIKUBE_IP:30080"
echo "   • Add to /etc/hosts: $MINIKUBE_IP relibank.local chaos.relibank.local"
echo ""
echo "📈 Monitor resources:"
echo "kubectl get pods -n relibank -w"
echo "kubectl get chaos -n relibank"
echo "kubectl get ingress --all-namespaces"
echo ""
echo "🔧 Start port-forwarding manually if needed:"
echo "skaffold port-forward --profile=local"

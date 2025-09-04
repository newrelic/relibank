#!/bin/bash

# Cleanup script for Relibank Kubernetes deployment
set -e

echo "🧹 Cleaning up Relibank Kubernetes deployment..."

# Stop chaos experiments first
echo "⏹️  Stopping chaos experiments..."
kubectl delete chaos --all -n relibank --ignore-not-found=true

# Delete Relibank namespace and all resources
echo "🗑️  Deleting Relibank namespace and resources..."
kubectl delete namespace relibank --ignore-not-found=true

# Optionally remove Chaos Mesh (uncomment if you want to remove it completely)
# echo "🗑️  Removing Chaos Mesh..."
# helm uninstall chaos_mesh -n chaos-system
# kubectl delete namespace chaos-system --ignore-not-found=true

echo "✅ Cleanup completed!"
echo "💡 To redeploy, run: ./deploy-k8s.sh"

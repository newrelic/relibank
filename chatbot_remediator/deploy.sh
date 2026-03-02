#!/bin/bash
set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELIBANK_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "${RELIBANK_ROOT}/.env" ]; then
    source "${RELIBANK_ROOT}/.env"
else
    echo "ERROR: .env file not found at ${RELIBANK_ROOT}/.env"
    exit 1
fi

# Configuration
NAMESPACE="chatbot-remediator"
AKS_CLUSTER="${AKS_CLUSTER_NAME:-relibank-aks}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-ReliBank}"

echo "=========================================="
echo "Deploying Chatbot Remediator to AKS"
echo "=========================================="
echo "Cluster: ${AKS_CLUSTER}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Namespace: ${NAMESPACE}"
echo ""

# Get AKS credentials
echo "Getting AKS credentials..."
az aks get-credentials --resource-group ${RESOURCE_GROUP} --name ${AKS_CLUSTER} --overwrite-existing

# Create namespace
echo ""
echo "Creating namespace..."
kubectl apply -f chatbot_remediator/k8s/namespace.yaml

# Create secrets from environment variables
echo ""
echo "Creating secrets..."
envsubst < chatbot_remediator/k8s/secrets.yaml.template | kubectl apply -f -

# Create ConfigMaps
echo ""
echo "Creating ConfigMaps..."
kubectl apply -f chatbot_remediator/k8s/configmap.yaml

# Deploy the application
echo ""
echo "Deploying application..."
kubectl apply -f chatbot_remediator/k8s/deployment.yaml

# Wait for deployment to be ready
echo ""
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/chatbot-remediator -n ${NAMESPACE} --timeout=300s

# Show deployment status
echo ""
echo "=========================================="
echo "Deployment Status"
echo "=========================================="
kubectl get pods -n ${NAMESPACE}
echo ""
kubectl get svc -n ${NAMESPACE}

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "To check logs:"
echo "  kubectl logs -n ${NAMESPACE} -l app=chatbot-remediator -f"
echo ""
echo "To port-forward:"
echo "  kubectl port-forward -n ${NAMESPACE} svc/chatbot-remediator 5004:80"
echo ""

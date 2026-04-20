#!/bin/bash
# Script to create Kubernetes secrets and configmaps for Azure OpenAI Assistants

set -e

echo "============================================"
echo "Azure OpenAI Kubernetes Setup"
echo "============================================"
echo ""

# Check if required environment variables are set
if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "ERROR: AZURE_OPENAI_ENDPOINT is not set"
    echo "Example: export AZURE_OPENAI_ENDPOINT='https://relibank-openai.openai.azure.com/'"
    exit 1
fi

if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo "ERROR: AZURE_OPENAI_API_KEY is not set"
    echo "Get your key from Azure Portal or run:"
    echo "  az cognitiveservices account keys list --name relibank-openai --resource-group relibank-ai-rg"
    exit 1
fi

if [ -z "$ASSISTANT_A_ID" ]; then
    echo "ERROR: ASSISTANT_A_ID is not set"
    echo "Run create_assistants.py first to create assistants"
    exit 1
fi

if [ -z "$ASSISTANT_B_ID" ]; then
    echo "ERROR: ASSISTANT_B_ID is not set"
    echo "Run create_assistants.py first to create assistants"
    exit 1
fi

# Set namespace (default: relibank)
NAMESPACE=${NAMESPACE:-relibank}

echo "Configuration:"
echo "  Namespace: $NAMESPACE"
echo "  Endpoint: $AZURE_OPENAI_ENDPOINT"
echo "  Assistant A ID: $ASSISTANT_A_ID"
echo "  Assistant B ID: $ASSISTANT_B_ID"
echo ""

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    echo "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
fi

# Delete existing secrets/configmaps if they exist
echo "Cleaning up existing resources..."
kubectl delete secret azure-openai-secrets -n "$NAMESPACE" 2>/dev/null || true
kubectl delete configmap azure-assistant-config -n "$NAMESPACE" 2>/dev/null || true

# Create secret for Azure OpenAI credentials
echo "Creating azure-openai-secrets..."
kubectl create secret generic azure-openai-secrets \
  --from-literal=endpoint="$AZURE_OPENAI_ENDPOINT" \
  --from-literal=api-key="$AZURE_OPENAI_API_KEY" \
  -n "$NAMESPACE"

echo "✓ Secret created: azure-openai-secrets"

# Create configmap for assistant IDs
echo "Creating azure-assistant-config..."
kubectl create configmap azure-assistant-config \
  --from-literal=assistant-a-id="$ASSISTANT_A_ID" \
  --from-literal=assistant-b-id="$ASSISTANT_B_ID" \
  -n "$NAMESPACE"

echo "✓ ConfigMap created: azure-assistant-config"

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Deploy the support service:"
echo "   kubectl apply -f k8s/base/services/support-service-deployment.yaml"
echo ""
echo "2. Check deployment status:"
echo "   kubectl get pods -n $NAMESPACE -l app=support-service"
echo ""
echo "3. View logs:"
echo "   kubectl logs -n $NAMESPACE -l app=support-service -f"
echo ""
echo "4. Test the service:"
echo "   kubectl port-forward -n $NAMESPACE svc/support-service 5003:5003"
echo "   curl -X POST http://localhost:5003/support-service/assistant/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\": \"Hello from Azure Assistants!\"}'"
echo ""

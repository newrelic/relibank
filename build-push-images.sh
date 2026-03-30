#!/bin/bash
# Configuration
ACR_NAME="relibank"
ACR_SERVER="${ACR_NAME}.azurecr.io"
REQUIRED_APP_NAME="ReliBank"
REQUIRED_CONTEXT="relibank-prod"
ENV_FILE="skaffold.env"
# List all services from skaffold.yaml
IMAGES=(
    "frontend-service"
    "accounts-service"
    "auth-service"
    "transaction-service"
    "bill-pay-service"
    "notifications-service"
    "scheduler-service"
    "mssql-custom"
    "postgres-custom"
    "support-service"
    "scenario-runner"
    "otel-collector-kafka"
    "kafka-with-monitoring"
)
# --- Validation Steps ---
echo "=== Step 1: Validating skaffold.env ==="
if [ ! -f "${ENV_FILE}" ]; then
    echo "ERROR: ${ENV_FILE} not found in current directory"
    exit 1
fi
# Check APP_NAME in skaffold.env
APP_NAME_LINE=$(grep "^APP_NAME=" "${ENV_FILE}")
if [ -z "${APP_NAME_LINE}" ]; then
    echo "ERROR: APP_NAME not found in ${ENV_FILE}"
    exit 1
fi
APP_NAME_VALUE=$(echo "${APP_NAME_LINE}" | cut -d'=' -f2)
if [ "${APP_NAME_VALUE}" != "${REQUIRED_APP_NAME}" ]; then
    echo "ERROR: APP_NAME in ${ENV_FILE} is '${APP_NAME_VALUE}', expected '${REQUIRED_APP_NAME}'"
    exit 1
fi
echo "✅ APP_NAME=${REQUIRED_APP_NAME} verified in ${ENV_FILE}"
echo ""
echo "=== Step 2: Validating Kubernetes context ==="
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "${CURRENT_CONTEXT}" != "${REQUIRED_CONTEXT}" ]; then
    echo "ERROR: Current Kubernetes context is '${CURRENT_CONTEXT}', expected '${REQUIRED_CONTEXT}'"
    echo "Switch context with: kubectl config use-context ${REQUIRED_CONTEXT}"
    exit 1
fi
echo "✅ Kubernetes context '${REQUIRED_CONTEXT}' verified"
echo ""
echo "=== Step 3: Running skaffold build ==="
echo "Building all images with loaded credentials..."
echo ""
# Source environment variables from skaffold.env
if [ -f "${ENV_FILE}" ]; then
    set -a
    source "${ENV_FILE}"
    set +a
    echo "✅ Loaded environment variables from ${ENV_FILE}"
fi
# Build all images (NOT using azure-prod profile to ensure all artifacts are built)
skaffold build --cache-artifacts=false --file-output=build-output.json
if [ $? -ne 0 ]; then
    echo "ERROR: skaffold build failed"
    exit 1
fi
echo "✅ Skaffold build completed"
echo ""
echo "=== Step 4: Logging into Azure Container Registry ==="
az acr login --name "${ACR_NAME}"
if [ $? -ne 0 ]; then
    echo "ERROR: ACR login failed. Please ensure you are logged in via 'az login' and have appropriate permissions."
    exit 1
fi
echo "✅ ACR login succeeded"
echo ""
echo "=== Step 5: Tagging and pushing images to ACR ==="
# Parse the build output to get actual image tags
for IMAGE_NAME in "${IMAGES[@]}"; do
    echo ""
    echo "--- Processing: ${IMAGE_NAME} ---"
    # Find the locally built image (skaffold tags with sha256)
    # List all tags for this image
    LOCAL_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "^${IMAGE_NAME}:")
    if [ -z "${LOCAL_IMAGES}" ]; then
        echo "WARNING: No local image found for ${IMAGE_NAME}. Skipping."
        continue
    fi
    # Get the first/latest image
    LOCAL_TAG=$(echo "${LOCAL_IMAGES}" | head -1)
    ACR_TAG="${ACR_SERVER}/${IMAGE_NAME}:latest"
    echo "1. Tagging ${LOCAL_TAG} -> ${ACR_TAG}"
    docker tag "${LOCAL_TAG}" "${ACR_TAG}"
    echo "2. Pushing ${ACR_TAG} to ACR..."
    docker push "${ACR_TAG}"
    if [ $? -ne 0 ]; then
        echo "ERROR: Push failed for ${IMAGE_NAME}. Stopping script."
        exit 1
    fi
    echo "✅ Push successful for ${IMAGE_NAME}"
done
echo ""
echo "=== Step 6: Cleanup ==="
echo "Removing temporary ACR tags from local machine..."
for IMAGE_NAME in "${IMAGES[@]}"; do
    docker rmi "${ACR_SERVER}/${IMAGE_NAME}:latest" 2>/dev/null
done
echo "✅ Cleanup complete"
echo ""
echo "=== Step 7: Applying manifests to AKS ==="
echo "Applying azure-prod overlay to cluster..."
kubectl apply -k k8s/overlays/azure-prod
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to apply manifests to AKS"
    exit 1
fi
echo "✅ Manifests applied successfully"
echo ""
echo "=== Step 8: Installing Chaos Mesh ==="
echo "Adding Chaos Mesh Helm repository..."
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update
echo ""
echo "Installing Chaos Mesh via Helm..."
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh \
  --create-namespace \
  --version 2.6.2 \
  -f scenario_service/chaos_mesh/values.yaml \
  --wait
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Chaos Mesh"
    exit 1
fi
echo "✅ Chaos Mesh installed successfully"
echo ""
echo "=== Step 9: Configuring Chaos Experiments ==="
echo "Labeling relibank namespace for chaos injection..."
kubectl label namespace relibank chaos-mesh.org/inject=enabled --overwrite
echo ""
echo "Applying chaos experiments..."
kubectl apply -f scenario_service/chaos_mesh/experiments/relibank-pod-chaos-adhoc.yaml
kubectl apply -f scenario_service/chaos_mesh/experiments/relibank-stress-scenarios.yaml
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to apply chaos experiments"
    exit 1
fi
echo "✅ Chaos experiments applied successfully"
echo ""
echo "========================================"
echo "✅ BUILD, PUSH, AND DEPLOY COMPLETE"
echo "========================================"
echo "All images successfully built and pushed to ${ACR_SERVER}"
echo "Manifests deployed to ${REQUIRED_CONTEXT}"
echo "Chaos Mesh installed and experiments configured"
echo ""
echo "Cleanup build output file..."
rm -f build-output.json

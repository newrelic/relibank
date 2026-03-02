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
IMAGE_NAME="chatbot-remediator"
ACR_NAME="${ACR_NAME:-relibankacr}"
FULL_IMAGE_NAME="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:latest"

echo "=========================================="
echo "Building Chatbot Remediator Service"
echo "=========================================="
echo "Image: ${FULL_IMAGE_NAME}"
echo ""

# Build the Docker image
echo "Building Docker image..."
docker build \
    --platform linux/amd64 \
    -f chatbot_remediator/Dockerfile \
    -t ${IMAGE_NAME}:latest \
    -t ${FULL_IMAGE_NAME} \
    --build-arg APP_NAME="${APP_NAME}" \
    --build-arg NEW_RELIC_ACCOUNT_ID="${NEW_RELIC_ACCOUNT_ID}" \
    --build-arg NEW_RELIC_LICENSE_KEY="${NEW_RELIC_LICENSE_KEY}" \
    --build-arg NEW_RELIC_USER_API_KEY="${NEW_RELIC_USER_API_KEY}" \
    --build-arg OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}" \
    --build-arg OPENAI_LOG="${OPENAI_LOG:-info}" \
    --build-arg OPENAI_BASE_URL="${AZURE_OPENAI_ENDPOINT}" \
    --build-arg OPENAI_API_VERSION="${OPENAI_API_VERSION:-2024-05-01-preview}" \
    --build-arg OPENAI_API_TYPE="azure" \
    --build-arg AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}" \
    --build-arg AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}" \
    --build-arg ASSISTANT_A_ID="${REMEDIATOR_COORDINATOR_ID}" \
    --build-arg ASSISTANT_B_ID="${REMEDIATOR_AGENT_ID}" \
    --build-arg ASSISTANT_B_DELAY_SECONDS="${REMEDIATOR_DELAY_SECONDS:-0}" \
    .

echo ""
echo "Pushing image to Azure Container Registry..."
docker push ${FULL_IMAGE_NAME}

echo ""
echo "=========================================="
echo "Build and push complete!"
echo "Image: ${FULL_IMAGE_NAME}"
echo "=========================================="

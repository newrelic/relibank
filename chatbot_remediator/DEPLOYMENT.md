# Chatbot Remediator Deployment Guide

## Overview

The Chatbot Remediator is a standalone service that uses Azure OpenAI's `remediator-agents` deployment (gpt-5.1-chat model) to coordinate and remediate system issues based on New Relic telemetry data.

**Components:**
- **Coordinator Agent**: Routes requests and coordinates remediation efforts
- **Remediator Agent**: Analyzes New Relic data and applies fixes

**Deployment:**
- Runs in its own `chatbot-remediator` namespace on AKS
- Independent from main ReliBank deployment
- Uses port 5004 (vs chatbot_service on 5003)

## Prerequisites

1. **Azure Resources:**
   - AKS cluster running
   - Azure Container Registry (ACR) access
   - Azure OpenAI deployment `remediator-agents` (gpt-5.1-chat)

2. **Environment Variables:**
   Add these to your `.env` file in the relibank root directory:
   ```bash
   # Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
   AZURE_OPENAI_API_KEY=<your-api-key>

   # Remediator Assistant IDs (created in step 1)
   REMEDIATOR_COORDINATOR_ID=<coordinator-assistant-id>
   REMEDIATOR_AGENT_ID=<remediator-assistant-id>

   # Optional: Add delay for demo purposes
   REMEDIATOR_DELAY_SECONDS=0

   # New Relic
   NEW_RELIC_ACCOUNT_ID=<your-account-id>
   NEW_RELIC_LICENSE_KEY=<your-license-key>
   NEW_RELIC_USER_API_KEY=<your-user-api-key>

   # Azure
   ACR_NAME=relibankacr
   AKS_CLUSTER_NAME=relibank-aks
   AZURE_RESOURCE_GROUP=ReliBank
   APP_NAME=ReliBank
   ```

## Deployment Steps

### Step 1: Create Azure OpenAI Assistants

```bash
cd /Users/jgoddard/git/relibank/chatbot_remediator
python3 create_assistants.py
```

**Expected output:**
```
Creating Coordinator Agent...
✓ Assistant A created: asst_xxxxx

Creating Remediator Agent...
✓ Assistant B created: asst_yyyyy

============================================================
SUCCESS! Copy these environment variables:
============================================================
export REMEDIATOR_COORDINATOR_ID=asst_xxxxx
export REMEDIATOR_AGENT_ID=asst_yyyyy
```

**Action:** Copy the assistant IDs and add them to your `.env` file:
```bash
REMEDIATOR_COORDINATOR_ID=asst_xxxxx
REMEDIATOR_AGENT_ID=asst_yyyyy
```

### Step 2: Update ConfigMap with Assistant IDs

Edit `k8s/configmap.yaml` and replace the placeholders:

```yaml
data:
  coordinator-id: "asst_xxxxx"  # Replace with actual ID
  remediator-id: "asst_yyyyy"   # Replace with actual ID
```

### Step 3: Build and Push Docker Image

```bash
cd /Users/jgoddard/git/relibank
./chatbot_remediator/build-and-push.sh
```

This will:
- Build the Docker image with correct environment variables
- Tag as `relibankacr.azurecr.io/chatbot-remediator:latest`
- Push to Azure Container Registry

### Step 4: Deploy to AKS

```bash
cd /Users/jgoddard/git/relibank
./chatbot_remediator/deploy.sh
```

This will:
- Create `chatbot-remediator` namespace
- Create secrets from `.env` file
- Create ConfigMaps
- Deploy the application
- Wait for pods to be ready

### Step 5: Verify Deployment

```bash
# Check pod status
kubectl get pods -n chatbot-remediator

# Check logs
kubectl logs -n chatbot-remediator -l app=chatbot-remediator -f

# Port forward to test locally
kubectl port-forward -n chatbot-remediator svc/chatbot-remediator 5004:80
```

Test the service:
```bash
curl http://localhost:5004/health
curl -X POST http://localhost:5004/chatbot-service/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze the high CPU usage on app-server-1 and remediate"}'
```

## Architecture

```
User Request
    ↓
chatbot-remediator:5004
    ↓
Coordinator Agent (remediator-agents)
    ↓
invoke_remediator_agent()
    ↓
Remediator Agent (remediator-agents)
    ↓
Response with remediation steps
```

## Differences from chatbot_service

| Feature | chatbot_service | chatbot_remediator |
|---------|----------------|-------------------|
| Port | 5003 | 5004 |
| Namespace | default (with ReliBank) | chatbot-remediator |
| Model | gpt-4-1 | remediator-agents (gpt-5.1-chat) |
| Purpose | Banking queries | System remediation |
| Coordinator | Banking coordinator | Remediation coordinator |
| Specialist | Financial specialist | Remediator agent |
| Deployment | With main app | Independent |

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod -n chatbot-remediator <pod-name>
kubectl logs -n chatbot-remediator <pod-name>
```

### Check secrets
```bash
kubectl get secrets -n chatbot-remediator
kubectl describe secret newrelic-secrets -n chatbot-remediator
```

### Check ConfigMaps
```bash
kubectl get configmap -n chatbot-remediator
kubectl describe configmap remediator-assistant-config -n chatbot-remediator
```

### Redeploy after changes
```bash
# Rebuild and push image
./chatbot_remediator/build-and-push.sh

# Restart deployment
kubectl rollout restart deployment/chatbot-remediator -n chatbot-remediator

# Or delete and redeploy
kubectl delete -f chatbot_remediator/k8s/deployment.yaml
kubectl apply -f chatbot_remediator/k8s/deployment.yaml
```

## Cleanup

To remove the deployment:
```bash
kubectl delete namespace chatbot-remediator
```

## Next Steps

1. **Expose externally**: Add Ingress or LoadBalancer service
2. **Add monitoring**: Configure New Relic dashboards for remediator service
3. **Connect to workflows**: Integrate with New Relic alerts/workflows to trigger remediations
4. **Add more tools**: Give remediator agent functions to call k8s API, restart services, etc.

## Files Structure

```
chatbot_remediator/
├── DEPLOYMENT.md              # This file
├── build-and-push.sh          # Build and push Docker image
├── deploy.sh                  # Deploy to AKS
├── create_assistants.py       # Create Azure OpenAI assistants
├── Dockerfile                 # Docker build configuration
├── chatbot_service.py         # FastAPI application (copied from chatbot_service)
├── requirements.txt           # Python dependencies
├── k8s/
│   ├── namespace.yaml         # Kubernetes namespace
│   ├── deployment.yaml        # Deployment and Service
│   ├── configmap.yaml         # ConfigMaps (assistant IDs)
│   └── secrets.yaml.template  # Secret template (don't commit actual secrets)
└── ... (other copied files)
```

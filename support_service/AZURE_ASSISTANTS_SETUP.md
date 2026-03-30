# Azure OpenAI Assistants Setup Guide

This guide walks through setting up Azure OpenAI Assistants with agent-to-agent communication for the Relibank support service.

## Overview

The support service now supports two modes:
1. **Existing**: Stateless chat via `/support-service/chat` (OpenAI + MCP tools)
2. **NEW**: Stateful assistant chat via `/support-service/assistant/chat` (Azure OpenAI Assistants)

The new assistant mode features:
- **Agent-to-Agent Communication**: Coordinator agent (A) can invoke specialist agent (B)
- **Comprehensive New Relic Instrumentation**: Tracks latency, tokens, costs, and distributed tracing
- **Demo Mode**: Artificial delay feature to demonstrate bottleneck identification

## Prerequisites

1. Azure subscription
2. Azure CLI installed
3. Python 3.12+
4. Kubernetes cluster (for deployment)

## Step 1: Create Azure Resources

### Create Resource Group and OpenAI Service

```bash
# Create resource group
az group create --name relibank-ai-rg --location eastus

# Create Azure OpenAI service
az cognitiveservices account create \
  --name relibank-openai \
  --resource-group relibank-ai-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Get the API key
az cognitiveservices account keys list \
  --name relibank-openai \
  --resource-group relibank-ai-rg
```

### Deploy GPT-4o Model

```bash
az cognitiveservices account deployment create \
  --resource-group relibank-ai-rg \
  --name relibank-openai \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-11-20" \
  --sku-capacity 50 \
  --sku-name "Standard"
```

## Step 2: Create Assistants

### Set Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT="https://relibank-openai.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key-here"
```

### Run Assistant Creation Script

```bash
cd /Users/galabastro/Documents/Projects/relibank/support_service
python create_assistants.py
```

This will output:
```
export ASSISTANT_A_ID=asst_xxxxxxxxxxxxx
export ASSISTANT_B_ID=asst_yyyyyyyyyyyyy
```

Save these IDs - you'll need them for configuration.

## Step 3: Local Testing

### Configure Environment

```bash
# Existing OpenAI configuration (keep as-is)
export OPENAI_API_KEY="your-existing-key"
export OPENAI_BASE_URL="your-existing-url"

# Azure OpenAI Assistants (new)
export AZURE_OPENAI_ENDPOINT="https://relibank-openai.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-azure-api-key"
export ASSISTANT_A_ID="asst_xxxxxxxxxxxxx"
export ASSISTANT_B_ID="asst_yyyyyyyyyyyyy"

# Optional: Demo mode (set to 8 to add 8-second delay to Assistant B)
export ASSISTANT_B_DELAY_SECONDS=0

# New Relic
export NEW_RELIC_LICENSE_KEY="your-nr-license-key"
```

### Run Service Locally

```bash
cd /Users/galabastro/Documents/Projects/relibank/support_service
newrelic-admin run-program uvicorn support_service:app --reload --host 0.0.0.0 --port 5003
```

### Test Existing Endpoint (should still work)

```bash
curl -X POST "http://localhost:5003/support-service/chat?prompt=What%20is%20Python"
```

### Test New Assistant Endpoint

```bash
# Simple query (Assistant A only)
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Relibank?"
  }'

# Complex query (triggers Assistant A → Assistant B)
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you analyze my spending patterns from last month and provide investment recommendations?"
  }'

# Continued conversation (use thread_id from previous response)
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What about my savings goals?",
    "thread_id": "thread_xxxxxxxxxxxxx"
  }'
```

## Step 4: Kubernetes Deployment

### Create Secrets

```bash
# Create Azure OpenAI secrets
kubectl create secret generic azure-openai-secrets \
  --from-literal=endpoint=https://relibank-openai.openai.azure.com/ \
  --from-literal=api-key=YOUR_AZURE_API_KEY \
  -n relibank

# Create assistant configuration
kubectl create configmap azure-assistant-config \
  --from-literal=assistant-a-id=asst_xxxxxxxxxxxxx \
  --from-literal=assistant-b-id=asst_yyyyyyyyyyyyy \
  -n relibank
```

### Deploy Service

```bash
kubectl apply -f /Users/galabastro/Documents/Projects/relibank/k8s/base/services/support-service-deployment.yaml
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n relibank -l app=support-service

# Check logs
kubectl logs -n relibank -l app=support-service -f

# Port forward for testing
kubectl port-forward -n relibank svc/support-service 5003:5003
```

## Step 5: Demo Feature - Intentional Slowdown

To demonstrate how New Relic helps identify bottlenecks:

### Enable Demo Mode

```bash
# Local: Set environment variable
export ASSISTANT_B_DELAY_SECONDS=8

# Kubernetes: Update deployment
kubectl set env deployment/support-service \
  ASSISTANT_B_DELAY_SECONDS=8 \
  -n relibank
```

### Test and Observe

```bash
# Send request that triggers Assistant B
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze my spending patterns"
  }'

# Response will take ~8+ seconds longer
```

### View in New Relic

```sql
-- Compare Assistant A vs B latency
SELECT average(latencyMs) as 'Average Latency (ms)'
FROM AzureAssistantInvocation
SINCE 1 hour ago FACET assistantName

-- See artificial delay impact
SELECT average(latencyMs), average(artificialDelayMs)
FROM AzureAssistantInvocation
WHERE assistantName = 'specialist'
SINCE 1 hour ago TIMESERIES

-- Overall impact on coordinator
SELECT average(latencyMs) as 'Overall Latency'
FROM AzureAssistantInvocation
WHERE assistantName = 'coordinator'
SINCE 1 hour ago FACET assistantBInvoked TIMESERIES
```

## New Relic Monitoring

### Custom Events

**AzureAssistantInvocation**
- `assistantId`, `assistantName` (coordinator/specialist)
- `threadId`, `latencyMs`, `totalTokens`, `estimatedCost`
- `assistantBInvoked` (true if agent-to-agent call occurred)
- `artificialDelayMs` (for demo mode)

**AgentToAgentCall**
- `sourceAgent`, `targetAgent`
- `threadId`, `functionName`

### Useful NRQL Queries

```sql
-- All assistant invocations
SELECT * FROM AzureAssistantInvocation SINCE 1 hour ago

-- Agent-to-agent calls
SELECT * FROM AgentToAgentCall SINCE 1 hour ago

-- Token usage by assistant
SELECT sum(totalTokens)
FROM AzureAssistantInvocation
SINCE 1 day ago FACET assistantName TIMESERIES

-- Cost analysis
SELECT sum(estimatedCost)
FROM AzureAssistantInvocation
SINCE 1 day ago TIMESERIES 1 hour

-- Latency percentiles
SELECT percentile(latencyMs, 50, 95, 99)
FROM AzureAssistantInvocation
SINCE 1 hour ago FACET assistantName TIMESERIES

-- Error rate
SELECT percentage(count(*), WHERE status = 'error')
FROM AzureAssistantInvocation
SINCE 1 hour ago TIMESERIES
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│          CHATBOT SERVICE (Port 5003)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  EXISTING:                                                  │
│  POST /support-service/chat                                 │
│    ↓                                                        │
│  AsyncOpenAI → gpt-4.1 → MCP Tools                          │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  NEW:                                                       │
│  POST /support-service/assistant/chat                       │
│    ↓                                                        │
│  Azure OpenAI Assistant A (Coordinator)                     │
│    ↓ (function: invoke_specialist_agent)                   │
│  Service Code Handles Function                              │
│    ↓                                                        │
│  Azure OpenAI Assistant B (Specialist)                      │
│    ↓                                                        │
│  New Relic (Custom Events, Metrics, Traces)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Agent-to-Agent Flow

1. User sends message to `/assistant/chat`
2. Service invokes Assistant A (Coordinator) with message
3. Assistant A determines if it needs specialist help
4. Assistant A calls function `invoke_specialist_agent(query="...")`
5. Service code receives function call
6. Service creates new thread and invokes Assistant B (Specialist)
7. Assistant B processes query and returns analysis
8. Service submits function output back to Assistant A
9. Assistant A synthesizes final response combining both agents
10. Response returned to user
11. All steps recorded in New Relic with distributed tracing

## Cost Estimation

**GPT-4o Pricing:**
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

**Example Conversation:**
- Simple query (A only): ~500 tokens = $0.0035
- Complex query (A→B): ~2000 tokens = $0.015
- Agent-to-agent adds ~3-5x cost vs single agent

Monitor costs in New Relic:
```sql
SELECT sum(estimatedCost) as 'Total Cost'
FROM AzureAssistantInvocation
SINCE 1 day ago TIMESERIES 1 hour
```

## Troubleshooting

### Assistant endpoint returns 503

**Problem**: `Azure OpenAI Assistants not configured`

**Solution**: Check environment variables are set:
```bash
echo $AZURE_OPENAI_ENDPOINT
echo $AZURE_OPENAI_API_KEY
echo $ASSISTANT_A_ID
echo $ASSISTANT_B_ID
```

### Existing /chat endpoint broken

**Problem**: Shouldn't happen - endpoints are independent

**Solution**: Check logs for OpenAI client initialization errors

### Assistant never invokes Assistant B

**Problem**: Query not complex enough to trigger function call

**Solution**: Use queries that require financial analysis:
- "Analyze my spending patterns"
- "Provide investment recommendations"
- "Help me optimize my budget"

### New Relic events not appearing

**Problem**: New Relic not configured or instrumentation not working

**Solution**:
1. Check `NEW_RELIC_LICENSE_KEY` is set
2. Verify `newrelic-admin run-program` is used to start service
3. Query with longer time range: `SINCE 1 hour ago`

## Optional: Disable Azure Assistants

If you want to run the service without Azure Assistants (existing functionality only):

1. Don't set Azure environment variables
2. Service will log: "Azure OpenAI not configured. Assistants endpoint will not be available."
3. `/chat` endpoint works normally
4. `/assistant/chat` returns 503

## Summary

You now have:
- ✅ Existing stateless chat endpoint (unchanged)
- ✅ New stateful assistant endpoint with agent-to-agent communication
- ✅ Comprehensive New Relic observability
- ✅ Demo mode to show bottleneck identification
- ✅ Cost tracking and optimization insights

For questions or issues, check the service logs or New Relic APM dashboard.

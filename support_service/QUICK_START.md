# Azure OpenAI Assistants - Quick Start Guide

## TL;DR

This adds **agent-to-agent communication** to the Relibank support using Azure OpenAI Assistants, with full New Relic observability.

## What's New

- ✅ New endpoint: `POST /support-service/assistant/chat`
- ✅ Agent-to-agent: Coordinator → Specialist flow
- ✅ Existing `/chat` endpoint unchanged
- ✅ Comprehensive New Relic instrumentation
- ✅ Demo mode to show bottleneck identification

## Quick Setup (5 Minutes)

### 1. Create Azure Resources

```bash
# Create resource group and OpenAI service
az group create --name relibank-ai-rg --location eastus
az cognitiveservices account create --name relibank-openai \
  --resource-group relibank-ai-rg --kind OpenAI --sku S0 --location eastus

# Deploy GPT-4o model
az cognitiveservices account deployment create \
  --resource-group relibank-ai-rg --name relibank-openai \
  --deployment-name gpt-4o --model-name gpt-4o \
  --model-version "2024-11-20" --sku-capacity 50 --sku-name "Standard"

# Get API key
az cognitiveservices account keys list \
  --name relibank-openai --resource-group relibank-ai-rg
```

### 2. Create Assistants

```bash
export AZURE_OPENAI_ENDPOINT="https://relibank-openai.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"

cd /Users/galabastro/Documents/Projects/relibank/support_service
python create_assistants.py

# Copy the output:
# export ASSISTANT_A_ID=asst_xxxxx
# export ASSISTANT_B_ID=asst_yyyyy
```

### 3. Test Locally

```bash
# Set all environment variables
export OPENAI_API_KEY="your-existing-key"
export OPENAI_BASE_URL="your-existing-url"
export AZURE_OPENAI_ENDPOINT="https://relibank-openai.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-azure-api-key"
export ASSISTANT_A_ID="asst_xxxxx"
export ASSISTANT_B_ID="asst_yyyyy"
export NEW_RELIC_LICENSE_KEY="your-nr-key"

# Run service
cd support_service
newrelic-admin run-program uvicorn support_service:app --reload --host 0.0.0.0 --port 5003

# In another terminal, test
bash test_assistants.sh
```

### 4. Deploy to Kubernetes

```bash
# Set environment variables (same as step 2)
export AZURE_OPENAI_ENDPOINT="..."
export AZURE_OPENAI_API_KEY="..."
export ASSISTANT_A_ID="..."
export ASSISTANT_B_ID="..."

# Create secrets and configmaps
bash setup_k8s_azure.sh

# Deploy
kubectl apply -f k8s/base/services/support-service-deployment.yaml

# Verify
kubectl get pods -n relibank -l app=support-service
kubectl logs -n relibank -l app=support-service -f
```

## Usage Examples

### Simple Query (Single Agent)

```bash
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is Relibank?"
  }'
```

### Complex Query (Agent-to-Agent)

```bash
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze my spending patterns and provide investment recommendations"
  }'
```

### Continued Conversation

```bash
# First message
response=$(curl -s -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to save for a house"}')

# Extract thread_id
thread_id=$(echo $response | jq -r '.thread_id')

# Continue conversation
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"How much should I save monthly?\",
    \"thread_id\": \"$thread_id\"
  }"
```

## Demo Mode (Show Bottleneck in New Relic)

```bash
# Enable 8-second delay in Assistant B
export ASSISTANT_B_DELAY_SECONDS=8

# Restart service, then test
curl -X POST http://localhost:5003/support-service/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze my spending"}'

# Response takes ~8+ seconds
# Check New Relic to see Assistant B as bottleneck
```

## New Relic Queries

```sql
-- All assistant invocations
SELECT * FROM AzureAssistantInvocation SINCE 1 hour ago

-- Agent-to-agent calls
SELECT * FROM AgentToAgentCall SINCE 1 hour ago

-- Compare Assistant A vs B latency
SELECT average(latencyMs) FROM AzureAssistantInvocation
SINCE 1 hour ago FACET assistantName

-- Cost analysis
SELECT sum(estimatedCost) FROM AzureAssistantInvocation
SINCE 1 day ago TIMESERIES 1 hour

-- Impact of agent-to-agent on latency
SELECT average(latencyMs) FROM AzureAssistantInvocation
WHERE assistantName = 'coordinator'
SINCE 1 hour ago FACET assistantBInvoked TIMESERIES
```

## Import New Relic Dashboard

1. Go to New Relic → Dashboards → Import Dashboard
2. Upload `newrelic_dashboard.json`
3. Select your account
4. View comprehensive metrics

## Architecture

```
User Request
    ↓
POST /support-service/assistant/chat
    ↓
Assistant A (Coordinator)
    ↓ (determines need for specialist)
Function Call: invoke_specialist_agent
    ↓
Service Code
    ↓
Assistant B (Specialist) [May have artificial delay if demo mode]
    ↓
Detailed Analysis
    ↓
Service Code
    ↓
Assistant A (Coordinator)
    ↓
Final Response (synthesized from both agents)
    ↓
User receives response

    [All steps instrumented in New Relic]
```

## Key Features

- **Backward Compatible**: Existing `/chat` endpoint unchanged
- **Optional**: Service works without Azure config (assistants disabled)
- **Stateful**: Threads maintain conversation history
- **Cost Tracking**: GPT-4o pricing tracked per request
- **Demo Mode**: Artificial delay to demonstrate bottleneck detection
- **Full Observability**: New Relic custom events, metrics, distributed tracing

## Files Modified

1. `support_service/support_service.py` - Added Azure Assistants support
2. `support_service/Dockerfile` - Added Azure env vars
3. `k8s/base/services/support-service-deployment.yaml` - Updated K8s config

## Files Created

1. `support_service/create_assistants.py` - Script to create assistants
2. `support_service/setup_k8s_azure.sh` - K8s setup script
3. `support_service/test_assistants.sh` - Test script
4. `support_service/newrelic_dashboard.json` - Dashboard config
5. `support_service/AZURE_ASSISTANTS_SETUP.md` - Detailed setup guide
6. `support_service/QUICK_START.md` - This file

## Troubleshooting

### Service returns 503 for /assistant/chat
- Check Azure env vars are set: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `ASSISTANT_A_ID`, `ASSISTANT_B_ID`

### Assistant never calls Assistant B
- Query needs to be complex enough (financial analysis, investment advice, spending patterns)

### New Relic events not appearing
- Verify `NEW_RELIC_LICENSE_KEY` is set
- Check service started with `newrelic-admin run-program`
- Wait 1-2 minutes for events to appear

### Existing /chat endpoint broken
- Shouldn't happen - completely independent
- Check `OPENAI_API_KEY` and `OPENAI_BASE_URL` still set

## Cost Estimates

**GPT-4o Pricing:**
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

**Typical Requests:**
- Simple (A only): ~500 tokens = $0.0035
- Complex (A→B): ~2000 tokens = $0.015
- Agent-to-agent adds ~3-5x cost

Monitor in New Relic:
```sql
SELECT sum(estimatedCost) as 'Daily Cost'
FROM AzureAssistantInvocation
SINCE 1 day ago
```

## Next Steps

1. ✅ Set up Azure resources
2. ✅ Create assistants
3. ✅ Test locally
4. ✅ Deploy to Kubernetes
5. ✅ Import New Relic dashboard
6. ✅ Test demo mode
7. ⬜ Configure alerts
8. ⬜ Optimize prompts
9. ⬜ Scale as needed

## Support

See `AZURE_ASSISTANTS_SETUP.md` for detailed documentation.

Check service logs:
```bash
# Local
tail -f logs/support_service.log

# Kubernetes
kubectl logs -n relibank -l app=support-service -f
```

View in New Relic APM → Support Service → Distributed Tracing

#!/bin/bash
# Test script for Azure OpenAI Assistants endpoints

set -e

# Configuration
BASE_URL=${BASE_URL:-http://localhost:5003}
VERBOSE=${VERBOSE:-0}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================"
echo "Azure OpenAI Assistants Test Suite"
echo "============================================"
echo "Base URL: $BASE_URL"
echo ""

# Function to run test
run_test() {
    local test_name=$1
    local endpoint=$2
    local data=$3

    echo -e "${BLUE}Test: $test_name${NC}"

    if [ $VERBOSE -eq 1 ]; then
        echo "Request:"
        echo "$data" | jq .
        echo ""
    fi

    response=$(curl -s -X POST "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data")

    if [ $? -eq 0 ]; then
        if echo "$response" | jq . > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Success${NC}"
            if [ $VERBOSE -eq 1 ]; then
                echo "Response:"
                echo "$response" | jq .
            else
                echo "$response" | jq -r '.response // .detail // "No response"' | head -c 200
                echo ""
            fi
            echo ""
            return 0
        else
            echo -e "${RED}✗ Failed - Invalid JSON response${NC}"
            echo "$response"
            echo ""
            return 1
        fi
    else
        echo -e "${RED}✗ Failed - Connection error${NC}"
        echo ""
        return 1
    fi
}

# Test 1: Health check
echo -e "${YELLOW}=== Test 1: Health Check ===${NC}"
curl -s "$BASE_URL/chatbot-service/health" | jq .
echo ""
echo ""

# Test 2: Existing chat endpoint (should still work)
echo -e "${YELLOW}=== Test 2: Existing Chat Endpoint ===${NC}"
response=$(curl -s "$BASE_URL/chatbot-service/chat?prompt=What%20is%20Python")
if echo "$response" | jq . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Existing endpoint still works${NC}"
    echo "$response" | jq -r '.response' | head -c 200
    echo ""
else
    echo -e "${RED}✗ Existing endpoint broken${NC}"
    echo "$response"
fi
echo ""
echo ""

# Test 3: Simple assistant query (no agent-to-agent)
echo -e "${YELLOW}=== Test 3: Simple Assistant Query ===${NC}"
run_test "Simple Query" \
    "/chatbot-service/assistant/chat" \
    '{
        "message": "What is Relibank?"
    }'

# Test 4: Complex assistant query (should trigger Assistant B)
echo -e "${YELLOW}=== Test 4: Complex Query (Agent-to-Agent) ===${NC}"
run_test "Financial Analysis Query" \
    "/chatbot-service/assistant/chat" \
    '{
        "message": "Can you analyze my spending patterns from last month and provide detailed investment recommendations based on my risk profile?"
    }'

# Test 5: Conversation with thread_id
echo -e "${YELLOW}=== Test 5: Continued Conversation ===${NC}"
echo "Step 1: Create new thread"
response1=$(curl -s -X POST "$BASE_URL/chatbot-service/assistant/chat" \
    -H "Content-Type: application/json" \
    -d '{
        "message": "I want to save money for a house"
    }')

thread_id=$(echo "$response1" | jq -r '.thread_id')
echo "Thread ID: $thread_id"
echo ""

echo "Step 2: Continue conversation in same thread"
run_test "Continued Conversation" \
    "/chatbot-service/assistant/chat" \
    "{
        \"message\": \"How much should I save each month?\",
        \"thread_id\": \"$thread_id\"
    }"

# Test 6: Multiple complex queries (stress test)
echo -e "${YELLOW}=== Test 6: Multiple Complex Queries ===${NC}"
for i in {1..3}; do
    echo "Query $i/3"
    run_test "Complex Query #$i" \
        "/chatbot-service/assistant/chat" \
        '{
            "message": "Analyze my portfolio and suggest optimizations"
        }' > /dev/null
done
echo -e "${GREEN}✓ All queries completed${NC}"
echo ""
echo ""

# Test 7: Error handling
echo -e "${YELLOW}=== Test 7: Error Handling ===${NC}"
echo "Testing invalid request format..."
response=$(curl -s -X POST "$BASE_URL/chatbot-service/assistant/chat" \
    -H "Content-Type: application/json" \
    -d '{
        "invalid_field": "test"
    }')

if echo "$response" | jq -r '.detail' | grep -q "Field required"; then
    echo -e "${GREEN}✓ Error handling works correctly${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected error response${NC}"
    echo "$response" | jq .
fi
echo ""
echo ""

# Summary
echo "============================================"
echo "Test Suite Complete"
echo "============================================"
echo ""
echo "Next Steps:"
echo "1. Check New Relic for custom events:"
echo "   SELECT * FROM AzureAssistantInvocation SINCE 10 minutes ago"
echo ""
echo "2. Check agent-to-agent calls:"
echo "   SELECT * FROM AgentToAgentCall SINCE 10 minutes ago"
echo ""
echo "3. View distributed traces in New Relic APM"
echo ""
echo "4. Test with demo mode (Assistant B delay):"
echo "   export ASSISTANT_B_DELAY_SECONDS=8"
echo "   # Restart service, then run: bash test_assistants.sh"
echo ""

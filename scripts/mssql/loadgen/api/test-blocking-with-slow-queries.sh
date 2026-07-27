#!/bin/bash

# Test Transaction Service Blocking with Slow Queries
# Creates a 5-minute blocking scenario with alternating adjust and slow query requests
# Usage: ./test-blocking-with-slow-queries.sh [host]
# Default host: localhost:5001

HOST="${1:-localhost:5001}"

echo "Starting extended blocking scenario (300 seconds / 5 minutes)..."
echo "Target host: $HOST"
echo ""
curl -s "http://$HOST/transaction-service/blocking?delay_seconds=300" > /tmp/blocking.json &
BLOCKING_PID=$!

sleep 5
echo "Blocking established. Sending continuous stream of alternating requests..."
echo "Sending requests every 2 seconds for 300 seconds (150 total requests)..."
echo ""

# Query types to rotate through
QUERY_TYPES=("summary" "account_analysis" "window_functions" "self_join" "complex_filter")
QUERY_INDEX=0

# Send continuous requests every 2 seconds for 300 seconds (150 requests total)
REQUEST_COUNT=0
for i in {1..150}; do
    REQUEST_COUNT=$((REQUEST_COUNT + 1))

    # Alternate between adjust and slow query
    if [ $((i % 2)) -eq 1 ]; then
        # Odd numbers: adjust request
        curl -s -X POST "http://$HOST/transaction-service/adjust-amount/BILL-1701?adjustment=1.00" > /tmp/request-$i.json &
        echo "  Request $i: adjust-amount (total: $REQUEST_COUNT)"
    else
        # Even numbers: slow query request
        QUERY_TYPE=${QUERY_TYPES[$QUERY_INDEX]}
        curl -s "http://$HOST/transaction-service/slow-query?query_type=$QUERY_TYPE&delay_seconds=3" > /tmp/request-$i.json &
        echo "  Request $i: slow-query ($QUERY_TYPE) (total: $REQUEST_COUNT)"

        # Rotate to next query type
        QUERY_INDEX=$(( (QUERY_INDEX + 1) % ${#QUERY_TYPES[@]} ))
    fi

    sleep 2
done

echo ""
echo "All requests sent. Checking for blocking..."
sleep 3
echo ""
echo "=== Checking for blocking in database ==="
kubectl exec -n relibank mssql-0 -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -d RelibankDB -C -Q "
SELECT
    r.session_id as BlockedSession,
    r.blocking_session_id as BlockingSession,
    r.wait_type,
    r.wait_time / 1000.0 as WaitSeconds
FROM sys.dm_exec_requests r
WHERE r.database_id = DB_ID('RelibankDB')
AND r.blocking_session_id != 0
"

echo ""
echo "Waiting for requests to complete..."
wait

echo ""
echo "=== Results ==="
echo "Blocking:"
cat /tmp/blocking.json
echo ""
echo ""
echo "Request Summary:"
ADJUST_SUCCESS=0
ADJUST_FAIL=0
SLOW_QUERY_SUCCESS=0
SLOW_QUERY_FAIL=0

for i in {1..150}; do
    if [ -f /tmp/request-$i.json ]; then
        if [ $((i % 2)) -eq 1 ]; then
            # Adjust request
            if grep -q "success" /tmp/request-$i.json 2>/dev/null; then
                ADJUST_SUCCESS=$((ADJUST_SUCCESS + 1))
            else
                ADJUST_FAIL=$((ADJUST_FAIL + 1))
            fi
        else
            # Slow query request
            if grep -q "success" /tmp/request-$i.json 2>/dev/null; then
                SLOW_QUERY_SUCCESS=$((SLOW_QUERY_SUCCESS + 1))
            else
                SLOW_QUERY_FAIL=$((SLOW_QUERY_FAIL + 1))
            fi
        fi
    fi
done

echo "  Adjust requests:"
echo "    Successful: $ADJUST_SUCCESS"
echo "    Failed: $ADJUST_FAIL"
echo ""
echo "  Slow query requests:"
echo "    Successful: $SLOW_QUERY_SUCCESS"
echo "    Failed: $SLOW_QUERY_FAIL"
echo ""
echo "  Total requests: 150"
echo ""
echo "Sample results (first 5 adjust, first 5 slow query):"
echo "  Adjust samples:"
for i in 1 3 5 7 9; do
    echo "    Request $i: $(cat /tmp/request-$i.json 2>/dev/null | head -c 80)..."
done
echo ""
echo "  Slow query samples:"
for i in 2 4 6 8 10; do
    echo "    Request $i: $(cat /tmp/request-$i.json 2>/dev/null | head -c 80)..."
done

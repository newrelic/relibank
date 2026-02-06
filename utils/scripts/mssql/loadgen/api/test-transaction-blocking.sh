#!/bin/bash

# Test Transaction Service Blocking with Continuous Request Stream
# Usage: ./test-transaction-blocking.sh [host]
# Default host: localhost:5001

HOST="${1:-localhost:5001}"

echo "Starting blocking scenario (120 seconds)..."
echo "Target host: $HOST"
echo ""
curl -s "http://$HOST/transaction-service/blocking?delay_seconds=120" > /tmp/blocking.json &
BLOCKING_PID=$!

sleep 5
echo "Blocking established. Sending continuous stream of adjust requests..."
echo "Sending requests every 2 seconds for 120 seconds..."
echo ""

# Send continuous adjust requests every 2 seconds for 120 seconds (60 requests total)
REQUEST_COUNT=0
for i in {1..60}; do
    curl -s -X POST "http://$HOST/transaction-service/adjust-amount/BILL-1701?adjustment=1.00" > /tmp/adjust-$i.json &
    REQUEST_COUNT=$((REQUEST_COUNT + 1))
    echo "  Adjust request $i started (total: $REQUEST_COUNT)"
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
echo "Adjustment Summary:"
SUCCESS_COUNT=0
FAIL_COUNT=0
for i in {1..60}; do
    if grep -q "success" /tmp/adjust-$i.json 2>/dev/null; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done
echo "  Successful requests: $SUCCESS_COUNT"
echo "  Failed requests: $FAIL_COUNT"
echo ""
echo "Sample results (first 5 and last 5):"
for i in 1 2 3 4 5; do
    echo "  Request $i: $(cat /tmp/adjust-$i.json 2>/dev/null | head -c 80)..."
done
echo "  ..."
for i in 56 57 58 59 60; do
    echo "  Request $i: $(cat /tmp/adjust-$i.json 2>/dev/null | head -c 80)..."
done

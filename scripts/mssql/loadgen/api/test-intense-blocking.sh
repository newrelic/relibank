#!/bin/bash

# Intense Transaction Blocking Test - 1 Minute
# Creates heavy blocking with rapid requests for better detection
# Usage: ./test-intense-blocking.sh [host]
# Default host: localhost:5001

HOST="${1:-localhost:5001}"

echo "Starting intense blocking scenario (60 seconds / 1 minute)..."
echo "Target host: $HOST"
echo ""
curl -s "http://$HOST/transaction-service/blocking?delay_seconds=60" > /tmp/blocking.json &
BLOCKING_PID=$!

sleep 3
echo "Blocking established. Sending rapid stream of requests..."
echo "Sending requests every 0.5 seconds for 60 seconds (120 total requests)..."
echo ""

# Send rapid requests every 0.5 seconds for 60 seconds (120 requests total)
# All adjust requests to create maximum blocking pressure
REQUEST_COUNT=0
for i in {1..120}; do
    curl -s -X POST "http://$HOST/transaction-service/adjust-amount/BILL-1701?adjustment=1.00" > /tmp/request-$i.json &
    REQUEST_COUNT=$((REQUEST_COUNT + 1))

    # Progress indicator every 10 requests
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Sent $i requests (total: $REQUEST_COUNT)"
    fi

    sleep 0.5
done

echo ""
echo "All requests sent. Checking for blocking..."
sleep 2
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
echo "Checking cumulative lock wait statistics..."
kubectl exec -n relibank mssql-0 -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -d RelibankDB -C -Q "
SELECT
    wait_type,
    waiting_tasks_count,
    wait_time_ms / 1000.0 AS wait_time_seconds,
    max_wait_time_ms / 1000.0 AS max_wait_time_seconds
FROM sys.dm_os_wait_stats
WHERE wait_type LIKE 'LCK%'
AND waiting_tasks_count > 0
ORDER BY wait_time_ms DESC
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
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in {1..120}; do
    if [ -f /tmp/request-$i.json ]; then
        if grep -q "success" /tmp/request-$i.json 2>/dev/null; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    fi
done

echo "  Successful requests: $SUCCESS_COUNT"
echo "  Failed requests: $FAIL_COUNT"
echo "  Total requests: 120"
echo ""
echo "Sample results (first 5 and last 5):"
for i in 1 2 3 4 5; do
    echo "  Request $i: $(cat /tmp/request-$i.json 2>/dev/null | head -c 80)..."
done
echo "  ..."
for i in 116 117 118 119 120; do
    echo "  Request $i: $(cat /tmp/request-$i.json 2>/dev/null | head -c 80)..."
done
echo ""
echo "Final lock wait statistics:"
kubectl exec -n relibank mssql-0 -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -d RelibankDB -C -Q "
SELECT
    wait_type,
    waiting_tasks_count,
    wait_time_ms / 1000.0 AS wait_time_seconds
FROM sys.dm_os_wait_stats
WHERE wait_type LIKE 'LCK%'
AND waiting_tasks_count > 0
ORDER BY wait_time_ms DESC
"

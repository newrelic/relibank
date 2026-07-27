#!/bin/bash

# Sustained Blocking Test - 2 Minutes
# Sends burst of requests at start, then sustained stream throughout blocking period
# Usage: ./test-sustained-blocking.sh [host]
# Default host: localhost:5001

HOST="${1:-localhost:5001}"

echo "Starting sustained blocking scenario (120 seconds / 2 minutes)..."
echo "Target host: $HOST"
echo ""
curl -s "http://$HOST/transaction-service/blocking?delay_seconds=120" > /tmp/blocking.json &
BLOCKING_PID=$!

sleep 3
echo "Blocking established. Sending burst of initial requests..."

# Send 30 rapid requests at the start to immediately create blocking
for i in {1..30}; do
    curl -s -X POST "http://$HOST/transaction-service/adjust-amount/BILL-1701?adjustment=1.00" > /tmp/request-$i.json &
done
echo "  Sent 30 initial burst requests"

sleep 2
echo ""
echo "Now sending sustained stream (1 request per second for 120 seconds)..."

# Continue sending requests every 1 second for the duration
for i in {31..150}; do
    curl -s -X POST "http://$HOST/transaction-service/adjust-amount/BILL-1701?adjustment=1.00" > /tmp/request-$i.json &

    if [ $((i % 20)) -eq 0 ]; then
        echo "  Sent $i requests total"
    fi

    sleep 1
done

echo ""
echo "All requests sent (150 total). Checking for active blocking..."
sleep 2
echo ""
echo "=== Checking for blocking in database NOW ==="
kubectl exec -n relibank mssql-0 -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -d RelibankDB -C -Q "
SELECT
    r.session_id as BlockedSession,
    r.blocking_session_id as BlockingSession,
    r.wait_type,
    r.wait_time / 1000.0 as WaitSeconds,
    r.command
FROM sys.dm_exec_requests r
WHERE r.database_id = DB_ID('RelibankDB')
AND r.blocking_session_id != 0
ORDER BY r.wait_time DESC
"

echo ""
echo "Checking blocked process count..."
kubectl exec -n relibank mssql-0 -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT COUNT(*) AS BlockedProcessCount
FROM sys.dm_exec_requests
WHERE blocking_session_id != 0
"

echo ""
echo "Waiting for all requests to complete..."
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

for i in {1..150}; do
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
echo "  Total requests: 150"
echo ""
echo "Final cumulative lock wait statistics:"
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

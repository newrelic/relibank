#!/bin/bash

# Create MSSQL Blocking Events for Testing
# This script creates blocking scenarios that New Relic can detect

echo "Creating blocking events in MSSQL..."

# First, let's check what databases exist
echo "Step 1: Checking available databases..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "SELECT name FROM sys.databases WHERE name NOT IN ('master','msdb','tempdb','model')"

echo ""
echo "Step 2: Creating test table and data in RelibankDB..."

# Create a test table if it doesn't exist
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'BlockingTest')
BEGIN
    CREATE TABLE BlockingTest (
        ID INT PRIMARY KEY,
        Value VARCHAR(100),
        UpdatedAt DATETIME
    );

    INSERT INTO BlockingTest (ID, Value, UpdatedAt) VALUES
    (1, 'Initial Value 1', GETDATE()),
    (2, 'Initial Value 2', GETDATE()),
    (3, 'Initial Value 3', GETDATE());
END

SELECT * FROM BlockingTest;
"

echo ""
echo "Step 3: Starting blocking transaction (Session 1 - will hold lock for 30 seconds)..."

# Start a long-running transaction that holds a lock (run in background)
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;

BEGIN TRANSACTION;
    UPDATE BlockingTest SET Value = 'Locked by Session 1', UpdatedAt = GETDATE() WHERE ID = 1;
    WAITFOR DELAY '00:00:30';
COMMIT TRANSACTION;
" &

BLOCKING_PID=$!
echo "Blocking transaction started (PID: $BLOCKING_PID)"

# Give the first transaction time to start
sleep 2

echo ""
echo "Step 4: Attempting to access locked row (Session 2 - will be blocked)..."

# Try to access the same row (this will be blocked)
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;
SELECT * FROM BlockingTest WHERE ID = 1;
UPDATE BlockingTest SET Value = 'Trying to update from Session 2' WHERE ID = 1;
" &

BLOCKED_PID=$!
echo "Blocked transaction started (PID: $BLOCKED_PID)"

echo ""
echo "Step 5: Checking for blocking (Session 3)..."
sleep 3

# Query to see blocking
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT
    blocking.session_id AS BlockingSessionID,
    blocked.session_id AS BlockedSessionID,
    blocked.wait_type AS WaitType,
    blocked.wait_time AS WaitTime_ms,
    blocked.wait_resource AS WaitResource,
    blocking_sql.text AS BlockingQuery,
    blocked_sql.text AS BlockedQuery
FROM sys.dm_exec_requests AS blocked
INNER JOIN sys.dm_exec_requests AS blocking
    ON blocked.blocking_session_id = blocking.session_id
CROSS APPLY sys.dm_exec_sql_text(blocking.sql_handle) AS blocking_sql
CROSS APPLY sys.dm_exec_sql_text(blocked.sql_handle) AS blocked_sql
WHERE blocked.blocking_session_id <> 0;
"

echo ""
echo "Blocking events created! New Relic should detect these."
echo "Waiting for transactions to complete..."

# Wait for both background processes
wait $BLOCKING_PID
wait $BLOCKED_PID

echo ""
echo "Step 6: Verifying final state..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;
SELECT * FROM BlockingTest;
"

echo ""
echo "Done! Check New Relic for blocking events."

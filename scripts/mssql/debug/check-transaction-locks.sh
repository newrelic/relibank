#!/bin/bash

echo "=========================================="
echo "MSSQL Transaction Lock Debugging"
echo "=========================================="
echo ""

# MSSQL Connection Details
SA_PASSWORD="YourStrong@Passwor\`!"
DATABASE="RelibankDB"
POD_NAME="mssql-0"
NAMESPACE="relibank"

echo "Step 1: Checking latest transaction with UPDLOCK, HOLDLOCK..."
echo "---"
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "$SA_PASSWORD" -d "$DATABASE" -C -Q "
SELECT TOP 1 TransactionID, BillID, Amount
FROM Transactions WITH (UPDLOCK, HOLDLOCK)
ORDER BY TransactionID DESC
"
echo ""

echo "Step 2: Displaying all transactions in the database..."
echo "---"
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "$SA_PASSWORD" -d "$DATABASE" -C -Q "
SELECT
    TransactionID,
    EventType,
    BillID,
    Amount,
    Currency,
    AccountID,
    CONVERT(VARCHAR, DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01'), 120) AS TransactionTime,
    StartDate,
    CancellationUserID,
    CancellationTimestamp
FROM Transactions
ORDER BY TransactionID DESC
"
echo ""

echo "Step 3: Transaction count..."
echo "---"
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "$SA_PASSWORD" -d "$DATABASE" -C -Q "
SELECT COUNT(*) AS TotalTransactions FROM Transactions
"
echo ""

echo "Step 4: Checking for any active locks..."
echo "---"
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "$SA_PASSWORD" -d "$DATABASE" -C -Q "
SELECT
    tl.request_session_id,
    tl.resource_type,
    tl.resource_database_id,
    tl.resource_associated_entity_id,
    tl.request_mode,
    tl.request_status
FROM sys.dm_tran_locks AS tl
WHERE tl.resource_database_id = DB_ID('$DATABASE')
"
echo ""

echo "=========================================="
echo "Debug Complete"
echo "=========================================="

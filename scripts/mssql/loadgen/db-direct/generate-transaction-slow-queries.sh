#!/bin/bash

# Generate Slow Queries Against Transactions Table
# Creates realistic transaction data and runs intentionally slow queries

echo "=========================================="
echo "Generating Slow Transaction Queries"
echo "=========================================="
echo ""

echo "Step 1: Populating Transactions table with test data..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -d RelibankDB -C -Q "
-- Populate with 5000 test transactions if not already populated
DECLARE @current_count INT;
SELECT @current_count = COUNT(*) FROM Transactions;

IF @current_count < 1000
BEGIN
    PRINT 'Adding test transactions...';

    DECLARE @i INT = 1;
    DECLARE @event_type VARCHAR(50);
    DECLARE @bill_id VARCHAR(50);
    DECLARE @amount DECIMAL(18,2);
    DECLARE @currency VARCHAR(10);
    DECLARE @account_id INT;
    DECLARE @timestamp FLOAT;

    WHILE @i <= 5000
    BEGIN
        -- Vary event types
        SET @event_type = CASE (@i % 5)
            WHEN 0 THEN 'BillPaymentInitiated'
            WHEN 1 THEN 'BillPaymentCompleted'
            WHEN 2 THEN 'BillPaymentCancelled'
            WHEN 3 THEN 'RecurringBillSetup'
            ELSE 'TransactionAdjustment'
        END;

        SET @bill_id = 'BILL-TEST-' + RIGHT('00000' + CAST((@i % 1000) AS VARCHAR), 5);
        SET @amount = (@i % 500) + ((@i % 100) / 100.0) + 10.00;
        SET @currency = CASE (@i % 3)
            WHEN 0 THEN 'USD'
            WHEN 1 THEN 'EUR'
            ELSE 'GBP'
        END;
        SET @account_id = 10000 + (@i % 500);
        SET @timestamp = DATEDIFF(s, '1970-01-01', DATEADD(DAY, -(@i % 365), GETDATE()));

        INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp)
        VALUES (@event_type, @bill_id, @amount, @currency, @account_id, @timestamp);

        SET @i = @i + 1;
    END

    PRINT 'Added 5000 test transactions';
END
ELSE
BEGIN
    PRINT 'Transactions table already populated with ' + CAST(@current_count AS VARCHAR) + ' records';
END

SELECT COUNT(*) AS TotalTransactions FROM Transactions;
"

echo ""
echo "Step 2: Running slow queries continuously..."
echo ""

# Function to run a query in background
run_query() {
    local query_name="$1"
    local query="$2"
    echo "Running: $query_name"
    kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -d RelibankDB -C -Q "$query" > /dev/null 2>&1 &
}

# Query 1: Slow aggregation by EventType with delay (3s)
run_query "Transaction Summary Report (3s)" "
SELECT
    EventType,
    COUNT(*) AS TransactionCount,
    SUM(Amount) AS TotalAmount,
    AVG(Amount) AS AvgAmount,
    MIN(Amount) AS MinAmount,
    MAX(Amount) AS MaxAmount,
    COUNT(DISTINCT BillID) AS UniqueBills,
    COUNT(DISTINCT AccountID) AS UniqueAccounts
FROM Transactions
GROUP BY EventType
ORDER BY TotalAmount DESC
WAITFOR DELAY '00:00:03';
"

sleep 1

# Query 2: Inefficient subquery for account analysis (4s)
run_query "Account Transaction Analysis (4s)" "
SELECT TOP 100
    AccountID,
    (SELECT COUNT(*) FROM Transactions t WHERE t.AccountID = main.AccountID) AS TotalTransactions,
    (SELECT SUM(Amount) FROM Transactions t WHERE t.AccountID = main.AccountID) AS TotalSpent,
    (SELECT MAX(Amount) FROM Transactions t WHERE t.AccountID = main.AccountID) AS LargestTransaction,
    (SELECT COUNT(DISTINCT BillID) FROM Transactions t WHERE t.AccountID = main.AccountID) AS UniqueBills
FROM (SELECT DISTINCT AccountID FROM Transactions) main
WAITFOR DELAY '00:00:04';
"

sleep 1

# Query 3: String operations on BillID (3s)
run_query "BillID Pattern Analysis (3s)" "
SELECT
    BillID,
    UPPER(BillID) AS UpperBillID,
    REVERSE(BillID) AS ReversedBillID,
    LEN(BillID) AS BillIDLength,
    SUBSTRING(BillID, 1, 4) AS BillPrefix,
    REPLACE(BillID, 'BILL-', '') AS BillNumber
FROM Transactions
WHERE BillID LIKE 'BILL-%'
WAITFOR DELAY '00:00:03';
"

sleep 1

# Query 4: Window functions for running totals (5s)
run_query "Running Balance Calculation (5s)" "
SELECT
    TransactionID,
    AccountID,
    EventType,
    Amount,
    DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01') AS TransactionDate,
    SUM(Amount) OVER (PARTITION BY AccountID ORDER BY TransactionID) AS RunningTotal,
    AVG(Amount) OVER (PARTITION BY AccountID ORDER BY TransactionID ROWS BETWEEN 10 PRECEDING AND CURRENT ROW) AS MovingAvg,
    ROW_NUMBER() OVER (PARTITION BY AccountID ORDER BY Amount DESC) AS AmountRank
FROM Transactions
WHERE EventType IN ('BillPaymentInitiated', 'BillPaymentCompleted')
WAITFOR DELAY '00:00:05';
"

sleep 1

# Query 5: Full table scan with complex WHERE clause (4s)
run_query "Complex Transaction Filter (4s)" "
SELECT *
FROM Transactions
WHERE Amount > 100.00
    AND LEN(BillID) > 10
    AND Currency IN ('USD', 'EUR')
    AND EventType LIKE '%Payment%'
ORDER BY Amount DESC, TransactionID DESC
WAITFOR DELAY '00:00:04';
"

sleep 1

# Query 6: Self-join for transaction matching (5s)
run_query "Duplicate Transaction Detection (5s)" "
SELECT
    t1.TransactionID AS Transaction1,
    t2.TransactionID AS Transaction2,
    t1.BillID,
    t1.Amount,
    t1.AccountID,
    ABS(t1.Amount - t2.Amount) AS AmountDifference
FROM Transactions t1
INNER JOIN Transactions t2
    ON t1.BillID = t2.BillID
    AND t1.AccountID = t2.AccountID
    AND t1.TransactionID < t2.TransactionID
WHERE ABS(t1.Amount - t2.Amount) < 1.00
WAITFOR DELAY '00:00:05';
"

sleep 1

# Query 7: Currency conversion aggregation (4s)
run_query "Currency Analysis (4s)" "
SELECT
    Currency,
    EventType,
    COUNT(*) AS TransactionCount,
    SUM(Amount) AS TotalAmount,
    AVG(Amount) AS AvgAmount,
    STDEV(Amount) AS StdDevAmount,
    MIN(DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01')) AS EarliestTransaction,
    MAX(DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01')) AS LatestTransaction
FROM Transactions
GROUP BY Currency, EventType
HAVING COUNT(*) > 5
ORDER BY TotalAmount DESC
WAITFOR DELAY '00:00:04';
"

sleep 1

# Query 8: Recursive CTE for transaction chains (6s)
run_query "Transaction Chain Analysis (6s)" "
WITH TransactionChain AS (
    SELECT
        TransactionID,
        BillID,
        AccountID,
        Amount,
        EventType,
        1 AS ChainLevel
    FROM Transactions
    WHERE EventType = 'BillPaymentInitiated'
    AND TransactionID <= 100

    UNION ALL

    SELECT
        t.TransactionID,
        t.BillID,
        t.AccountID,
        t.Amount,
        t.EventType,
        tc.ChainLevel + 1
    FROM Transactions t
    INNER JOIN TransactionChain tc
        ON t.BillID = tc.BillID
        AND t.TransactionID > tc.TransactionID
    WHERE tc.ChainLevel < 5
)
SELECT
    BillID,
    COUNT(*) AS ChainLength,
    SUM(Amount) AS TotalAmount,
    MAX(ChainLevel) AS MaxLevel
FROM TransactionChain
GROUP BY BillID
ORDER BY ChainLength DESC
WAITFOR DELAY '00:00:06';
"

sleep 1

# Query 9: Non-SARGable timestamp conversion (5s)
run_query "Date Range Analysis (5s)" "
SELECT
    CONVERT(DATE, DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01')) AS TransactionDate,
    COUNT(*) AS DailyTransactions,
    SUM(Amount) AS DailyTotal,
    AVG(Amount) AS DailyAverage
FROM Transactions
WHERE YEAR(DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01')) = YEAR(GETDATE())
    AND MONTH(DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01')) = MONTH(GETDATE())
GROUP BY CONVERT(DATE, DATEADD(SECOND, CAST(Timestamp AS BIGINT), '1970-01-01'))
ORDER BY TransactionDate DESC
WAITFOR DELAY '00:00:05';
"

sleep 1

# Query 10: Cross join for bill combinations (4s)
run_query "Bill Combination Analysis (4s)" "
SELECT TOP 100
    t1.BillID AS BillID1,
    t2.BillID AS BillID2,
    t1.Amount + t2.Amount AS CombinedAmount,
    t1.AccountID
FROM Transactions t1
CROSS JOIN Transactions t2
WHERE t1.TransactionID < 500
    AND t2.TransactionID < 500
    AND t1.AccountID = t2.AccountID
    AND t1.BillID <> t2.BillID
WAITFOR DELAY '00:00:04';
"

echo ""
echo "Waiting for queries to complete..."
wait

echo ""
echo "=========================================="
echo "Slow Transaction Query Generation Complete!"
echo "=========================================="
echo ""
echo "Queries run:"
echo "  - Transaction Summary Report (3s)"
echo "  - Account Transaction Analysis (4s)"
echo "  - BillID Pattern Analysis (3s)"
echo "  - Running Balance Calculation (5s)"
echo "  - Complex Transaction Filter (4s)"
echo "  - Duplicate Transaction Detection (5s)"
echo "  - Currency Analysis (4s)"
echo "  - Transaction Chain Analysis (6s)"
echo "  - Date Range Analysis (5s)"
echo "  - Bill Combination Analysis (4s)"
echo ""
echo "Total execution time: ~42 seconds"
echo ""
echo "Check New Relic for slow query metrics!"
echo "Run this script continuously in a loop for sustained demo traffic:"
echo "  while true; do bash scripts/mssql/loadgen/db-direct/generate-transaction-slow-queries.sh; sleep 30; done"

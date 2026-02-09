#!/bin/bash

# Continuously populate DMV Plan Cache
# Runs queries every 30 seconds to keep them in the plan cache
# Press Ctrl+C to stop

echo "Starting continuous DMV plan cache population..."
echo "This will execute slow queries every 30 seconds"
echo "Press Ctrl+C to stop"
echo ""

COUNT=0
while true; do
    COUNT=$((COUNT + 1))
    echo "=== Iteration $COUNT at $(date) ==="

    kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;

-- Execute queries that will show up in DMV cache
-- Each query is executed once per iteration

-- Query 1: Recursive CTE
WITH RecursiveSales AS (
    SELECT SaleID, ProductID, TotalAmount, 1 AS Level
    FROM DemoSales WHERE SaleID <= 100
    UNION ALL
    SELECT s.SaleID, s.ProductID, s.TotalAmount, rs.Level + 1
    FROM DemoSales s
    INNER JOIN RecursiveSales rs ON s.ProductID = rs.ProductID
    WHERE rs.Level < 3 AND s.SaleID > rs.SaleID
)
SELECT TOP 10 ProductID, COUNT(*) AS RecursiveCount
FROM RecursiveSales
GROUP BY ProductID
ORDER BY RecursiveCount DESC;

-- Query 2: Complex aggregation
SELECT
    p.Category,
    COUNT(DISTINCT p.ProductID) AS UniqueProducts,
    COUNT(s.SaleID) AS TotalSales,
    SUM(s.TotalAmount) AS TotalRevenue
FROM DemoProducts p
LEFT JOIN DemoSales s ON p.ProductID = s.ProductID
GROUP BY p.Category;

-- Query 3: Window functions
SELECT TOP 10
    SaleID, ProductID, TotalAmount,
    ROW_NUMBER() OVER (PARTITION BY ProductID ORDER BY SaleDate DESC) AS SaleRank
FROM DemoSales
WHERE TotalAmount > 100
ORDER BY SaleDate DESC;
" 2>&1 | grep -E "(rows affected|Query|Error)" | head -20

    # Check how many queries are in the cache
    CACHE_COUNT=$(kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -h -1 -Q "SELECT COUNT(*) FROM sys.dm_exec_query_stats" 2>/dev/null | tr -d '[:space:]')

    echo "Queries in DMV cache: $CACHE_COUNT"
    echo "Waiting 30 seconds..."
    echo ""

    sleep 30
done

#!/bin/bash

# Populate DMV Plan Cache
# This script executes queries multiple times to ensure they appear in sys.dm_exec_query_stats
# The DMV plan cache is in-memory and volatile, so queries need to be executed recently

echo "Populating DMV plan cache with slow queries..."

kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;

-- Clear the plan cache first (optional - forces fresh plans)
-- DBCC FREEPROCCACHE;

PRINT 'Executing queries to populate plan cache...';

-- Query 1: Recursive CTE (slow query)
DECLARE @i INT = 0;
WHILE @i < 5
BEGIN
    WITH RecursiveSales AS (
        SELECT
            SaleID,
            ProductID,
            TotalAmount,
            1 AS Level
        FROM DemoSales
        WHERE SaleID <= 100

        UNION ALL

        SELECT
            s.SaleID,
            s.ProductID,
            s.TotalAmount,
            rs.Level + 1
        FROM DemoSales s
        INNER JOIN RecursiveSales rs ON s.ProductID = rs.ProductID
        WHERE rs.Level < 3
        AND s.SaleID > rs.SaleID
    )
    SELECT ProductID, COUNT(*) AS RecursiveCount, SUM(TotalAmount) AS TotalAmount
    FROM RecursiveSales
    GROUP BY ProductID
    ORDER BY RecursiveCount DESC;

    SET @i = @i + 1;
END
PRINT 'Query 1 executed 5 times';

-- Query 2: Complex JOIN and aggregation
SET @i = 0;
WHILE @i < 5
BEGIN
    SELECT
        p.Category,
        COUNT(DISTINCT p.ProductID) AS UniqueProducts,
        COUNT(s.SaleID) AS TotalSales,
        SUM(s.TotalAmount) AS TotalRevenue,
        MIN(s.SaleDate) AS FirstSale,
        MAX(s.SaleDate) AS LastSale
    FROM DemoProducts p
    LEFT JOIN DemoSales s ON p.ProductID = s.ProductID
    GROUP BY p.Category
    ORDER BY TotalRevenue DESC;

    SET @i = @i + 1;
END
PRINT 'Query 2 executed 5 times';

-- Query 3: Window functions
SET @i = 0;
WHILE @i < 5
BEGIN
    SELECT
        SaleID,
        ProductID,
        TotalAmount,
        ROW_NUMBER() OVER (PARTITION BY ProductID ORDER BY SaleDate DESC) AS SaleRank,
        SUM(TotalAmount) OVER (PARTITION BY ProductID) AS ProductTotal,
        AVG(TotalAmount) OVER (ORDER BY SaleDate ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS MovingAvg
    FROM DemoSales
    WHERE TotalAmount > 100
    ORDER BY SaleDate DESC;

    SET @i = @i + 1;
END
PRINT 'Query 3 executed 5 times';

-- Query 4: Cross join (intentionally slow)
SET @i = 0;
WHILE @i < 3
BEGIN
    SELECT TOP 100
        p1.ProductName AS Product1,
        p2.ProductName AS Product2,
        p1.Price + p2.Price AS CombinedPrice
    FROM DemoProducts p1
    CROSS JOIN DemoProducts p2
    WHERE p1.ProductID < 100 AND p2.ProductID < 100
    ORDER BY CombinedPrice DESC;

    SET @i = @i + 1;
END
PRINT 'Query 4 executed 3 times';

PRINT 'All queries executed successfully!';
PRINT '';
PRINT 'Checking DMV plan cache...';

-- Verify queries are in the cache
SELECT
    qs.execution_count,
    qs.total_elapsed_time / 1000 AS total_elapsed_ms,
    (qs.total_elapsed_time / 1000) / NULLIF(qs.execution_count, 0) AS avg_elapsed_ms,
    SUBSTRING(st.text, 1, 200) AS sql_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
WHERE st.text LIKE '%RecursiveSales%'
   OR st.text LIKE '%DemoProducts p%'
   OR st.text LIKE '%ROW_NUMBER%'
   OR st.text LIKE '%CROSS JOIN%'
ORDER BY qs.execution_count DESC;
"

echo ""
echo "Done! Queries should now be in the DMV plan cache."
echo "Check with: kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor\`!' -C -Q 'SELECT COUNT(*) FROM sys.dm_exec_query_stats'"

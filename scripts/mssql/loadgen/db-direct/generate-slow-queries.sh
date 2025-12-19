#!/bin/bash

# Generate Slow Queries for New Relic Demo
# Creates various patterns of legitimately slow queries with delays and inefficient operations

echo "=========================================="
echo "Generating Slow Queries for Demo"
echo "=========================================="
echo ""

# Function to run a query in background
run_query() {
    local query_name="$1"
    local query="$2"
    echo "Running: $query_name"
    kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -d RelibankDB -C -Q "$query" > /dev/null 2>&1 &
}

echo "Step 1: Creating demo tables if needed..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -d RelibankDB -C -Q "
-- Ensure demo tables exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DemoProducts')
BEGIN
    CREATE TABLE DemoProducts (
        ProductID INT PRIMARY KEY,
        ProductName VARCHAR(100),
        Category VARCHAR(50),
        Price DECIMAL(10,2),
        StockQuantity INT,
        LastUpdated DATETIME DEFAULT GETDATE()
    );

    -- Insert 5000 products
    DECLARE @i INT = 1;
    WHILE @i <= 5000
    BEGIN
        INSERT INTO DemoProducts (ProductID, ProductName, Category, Price, StockQuantity)
        VALUES (
            @i,
            'Product ' + CAST(@i AS VARCHAR(10)),
            CASE (@i % 5)
                WHEN 0 THEN 'Electronics'
                WHEN 1 THEN 'Clothing'
                WHEN 2 THEN 'Food'
                WHEN 3 THEN 'Books'
                ELSE 'Home & Garden'
            END,
            (@i % 500) + 9.99,
            (@i % 100) + 1
        );
        SET @i = @i + 1;
    END
    PRINT 'Created DemoProducts table';
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DemoSales')
BEGIN
    CREATE TABLE DemoSales (
        SaleID INT PRIMARY KEY,
        ProductID INT,
        SaleDate DATETIME,
        Quantity INT,
        TotalAmount DECIMAL(10,2)
    );

    -- Insert 10000 sales records
    DECLARE @j INT = 1;
    WHILE @j <= 10000
    BEGIN
        INSERT INTO DemoSales (SaleID, ProductID, SaleDate, Quantity, TotalAmount)
        VALUES (
            @j,
            (@j % 5000) + 1,
            DATEADD(DAY, -(@j % 365), GETDATE()),
            (@j % 10) + 1,
            ((@j % 10) + 1) * ((@j % 500) + 9.99)
        );
        SET @j = @j + 1;
    END
    PRINT 'Created DemoSales table';
END

SELECT 'Tables ready' AS Status;
"

echo ""
echo "Step 2: Running slow queries continuously..."
echo ""

# Query 1: Slow aggregation with 2-second delay
run_query "Slow Report with Delay (2s)" "
SELECT
    'Slow Sales Report' AS ReportType,
    Category,
    COUNT(DISTINCT s.SaleID) AS TotalSales,
    SUM(s.TotalAmount) AS Revenue,
    AVG(p.Price) AS AvgPrice
FROM DemoProducts p
JOIN DemoSales s ON p.ProductID = s.ProductID
GROUP BY Category
ORDER BY Revenue DESC
WAITFOR DELAY '00:00:02';
"

sleep 1

# Query 2: Inefficient subquery with delay
run_query "Inefficient Subquery (3s)" "
SELECT
    p.ProductID,
    p.ProductName,
    p.Category,
    (SELECT COUNT(*) FROM DemoSales WHERE ProductID = p.ProductID) AS SalesCount,
    (SELECT SUM(TotalAmount) FROM DemoSales WHERE ProductID = p.ProductID) AS TotalRevenue
FROM DemoProducts p
WHERE p.StockQuantity < 20
WAITFOR DELAY '00:00:03';
"

sleep 1

# Query 3: Cross join with delay (very slow)
run_query "Cartesian Product (5s)" "
SELECT TOP 100
    p1.ProductName AS Product1,
    p2.ProductName AS Product2,
    p1.Price + p2.Price AS CombinedPrice
FROM DemoProducts p1
CROSS JOIN DemoProducts p2
WHERE p1.ProductID < 100 AND p2.ProductID < 100
WAITFOR DELAY '00:00:05';
"

sleep 1

# Query 4: String operations with delay
run_query "Heavy String Processing (4s)" "
SELECT
    ProductID,
    UPPER(ProductName) AS UpperName,
    REVERSE(ProductName) AS ReverseName,
    REPLICATE(Category, 5) AS RepeatedCategory,
    LEN(ProductName) AS NameLength
FROM DemoProducts
WHERE ProductName LIKE '%Product%'
WAITFOR DELAY '00:00:04';
"

sleep 1

# Query 5: Window functions with delay
run_query "Window Functions (3s)" "
SELECT
    SaleID,
    ProductID,
    TotalAmount,
    ROW_NUMBER() OVER (PARTITION BY ProductID ORDER BY SaleDate DESC) AS SaleRank,
    SUM(TotalAmount) OVER (PARTITION BY ProductID) AS ProductTotal,
    AVG(TotalAmount) OVER (ORDER BY SaleDate ROWS BETWEEN 10 PRECEDING AND CURRENT ROW) AS MovingAvg
FROM DemoSales
WHERE SaleDate >= DATEADD(MONTH, -6, GETDATE())
WAITFOR DELAY '00:00:03';
"

sleep 1

# Query 6: Full table scan with sorting (2s)
run_query "Full Scan with Sort (2s)" "
SELECT *
FROM DemoSales
WHERE TotalAmount > 100
ORDER BY SaleDate DESC, TotalAmount DESC
WAITFOR DELAY '00:00:02';
"

sleep 1

# Query 7: Multiple joins with delay
run_query "Complex Join (4s)" "
SELECT
    p.Category,
    COUNT(DISTINCT p.ProductID) AS UniqueProducts,
    COUNT(s.SaleID) AS TotalSales,
    SUM(s.TotalAmount) AS TotalRevenue,
    MIN(s.SaleDate) AS FirstSale,
    MAX(s.SaleDate) AS LastSale
FROM DemoProducts p
LEFT JOIN DemoSales s ON p.ProductID = s.ProductID
LEFT JOIN DemoSales s2 ON p.ProductID = s2.ProductID AND s2.TotalAmount > 100
GROUP BY p.Category
HAVING COUNT(s.SaleID) > 5
WAITFOR DELAY '00:00:04';
"

sleep 1

# Query 8: Recursive CTE with delay (slow)
run_query "Recursive CTE (6s)" "
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
    WHERE rs.Level < 3 AND s.SaleID > rs.SaleID
)
SELECT
    ProductID,
    COUNT(*) AS RecursiveCount,
    SUM(TotalAmount) AS TotalAmount
FROM RecursiveSales
GROUP BY ProductID
ORDER BY RecursiveCount DESC
WAITFOR DELAY '00:00:06';
"

sleep 1

# Query 9: DISTINCT aggregation with delay
run_query "Distinct Aggregation (3s)" "
SELECT
    Category,
    COUNT(DISTINCT ProductID) AS UniqueProducts,
    COUNT(DISTINCT CAST(Price AS INT)) AS UniquePricePoints,
    SUM(DISTINCT StockQuantity) AS DistinctStockLevels
FROM DemoProducts
GROUP BY Category
WAITFOR DELAY '00:00:03';
"

sleep 1

# Query 10: Non-SARGable predicate with delay
run_query "Non-SARGable Query (5s)" "
SELECT *
FROM DemoProducts
WHERE SUBSTRING(ProductName, 1, 7) = 'Product'
AND LEN(Category) > 4
AND YEAR(LastUpdated) = YEAR(GETDATE())
WAITFOR DELAY '00:00:05';
"

echo ""
echo "Waiting for queries to complete..."
wait

echo ""
echo "=========================================="
echo "Slow Query Generation Complete!"
echo "=========================================="
echo ""
echo "Queries run:"
echo "  - Slow Report with Delay (2s)"
echo "  - Inefficient Subquery (3s)"
echo "  - Cartesian Product (5s)"
echo "  - Heavy String Processing (4s)"
echo "  - Window Functions (3s)"
echo "  - Full Scan with Sort (2s)"
echo "  - Complex Join (4s)"
echo "  - Recursive CTE (6s)"
echo "  - Distinct Aggregation (3s)"
echo "  - Non-SARGable Query (5s)"
echo ""
echo "Total execution time: ~40 seconds"
echo ""
echo "Check New Relic for MSSQLTopSlowQueries and MSSQLQueryExecutionPlans events!"
echo "Run this script continuously in a loop for sustained demo traffic:"
echo "  while true; do bash scripts/mssql/loadgen/db-direct/generate-slow-queries.sh; sleep 30; done"

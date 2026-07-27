#!/bin/bash

# Generate Query Load for MSSQL New Relic Monitoring
# Creates various inefficient queries to populate plan cache and generate execution plans

echo "Generating query load on RelibankDB..."
echo "This will create various query patterns for New Relic to monitor"
echo ""

# Step 1: Create test tables with data if they don't exist
echo "Step 1: Setting up test tables..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;

-- Create a numbers table for generating load
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Numbers')
BEGIN
    CREATE TABLE Numbers (
        ID INT PRIMARY KEY,
        Value INT,
        Description VARCHAR(100)
    );

    -- Insert 10000 rows
    DECLARE @i INT = 1;
    WHILE @i <= 10000
    BEGIN
        INSERT INTO Numbers (ID, Value, Description)
        VALUES (@i, @i * 2, 'Number ' + CAST(@i AS VARCHAR(10)));
        SET @i = @i + 1;
    END
    PRINT 'Created Numbers table with 10000 rows';
END

-- Create a customers table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Customers')
BEGIN
    CREATE TABLE Customers (
        CustomerID INT PRIMARY KEY,
        FirstName VARCHAR(50),
        LastName VARCHAR(50),
        Email VARCHAR(100),
        City VARCHAR(50)
    );

    -- Insert 1000 customers
    DECLARE @j INT = 1;
    WHILE @j <= 1000
    BEGIN
        INSERT INTO Customers (CustomerID, FirstName, LastName, Email, City)
        VALUES (
            @j,
            'First' + CAST(@j AS VARCHAR(10)),
            'Last' + CAST(@j AS VARCHAR(10)),
            'email' + CAST(@j AS VARCHAR(10)) + '@example.com',
            CASE (@j % 5)
                WHEN 0 THEN 'New York'
                WHEN 1 THEN 'Los Angeles'
                WHEN 2 THEN 'Chicago'
                WHEN 3 THEN 'Houston'
                ELSE 'Phoenix'
            END
        );
        SET @j = @j + 1;
    END
    PRINT 'Created Customers table with 1000 rows';
END

-- Create orders table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Orders')
BEGIN
    CREATE TABLE Orders (
        OrderID INT PRIMARY KEY,
        CustomerID INT,
        OrderDate DATETIME,
        Amount DECIMAL(10,2),
        Status VARCHAR(20)
    );

    -- Insert 5000 orders
    DECLARE @k INT = 1;
    WHILE @k <= 5000
    BEGIN
        INSERT INTO Orders (OrderID, CustomerID, OrderDate, Amount, Status)
        VALUES (
            @k,
            (@k % 1000) + 1,
            DATEADD(DAY, -(@k % 365), GETDATE()),
            (@k % 1000) + 10.50,
            CASE (@k % 4)
                WHEN 0 THEN 'Pending'
                WHEN 1 THEN 'Shipped'
                WHEN 2 THEN 'Delivered'
                ELSE 'Cancelled'
            END
        );
        SET @k = @k + 1;
    END
    PRINT 'Created Orders table with 5000 rows';
END

SELECT 'Setup complete' AS Status;
"

echo ""
echo "Step 2: Running inefficient queries to populate plan cache..."
echo ""

# Query 1: Table scan without index
echo "Query 1: Full table scan..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT * FROM Numbers WHERE Description LIKE '%500%';
" > /dev/null 2>&1 &

sleep 2

# Query 2: Cartesian product (cross join)
echo "Query 2: Cartesian product..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT TOP 100 c1.CustomerID, c2.CustomerID
FROM Customers c1, Customers c2
WHERE c1.CustomerID < 50 AND c2.CustomerID < 50;
" > /dev/null 2>&1 &

sleep 2

# Query 3: Multiple joins with aggregation
echo "Query 3: Complex join with aggregation..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT
    c.City,
    COUNT(o.OrderID) as OrderCount,
    SUM(o.Amount) as TotalAmount,
    AVG(o.Amount) as AvgAmount
FROM Customers c
LEFT JOIN Orders o ON c.CustomerID = o.CustomerID
GROUP BY c.City
HAVING COUNT(o.OrderID) > 10
ORDER BY TotalAmount DESC;
" > /dev/null 2>&1 &

sleep 2

# Query 4: Subquery in WHERE clause
echo "Query 4: Correlated subquery..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT c.CustomerID, c.FirstName, c.LastName
FROM Customers c
WHERE c.CustomerID IN (
    SELECT o.CustomerID
    FROM Orders o
    WHERE o.Amount > 500
    AND o.Status = 'Delivered'
);
" > /dev/null 2>&1 &

sleep 2

# Query 5: String operations (expensive)
echo "Query 5: String concatenation..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT
    CustomerID,
    UPPER(FirstName) + ' ' + UPPER(LastName) as FullName,
    REVERSE(Email) as ReversedEmail,
    REPLICATE(City, 3) as TripleCity
FROM Customers
WHERE LEN(FirstName) > 5;
" > /dev/null 2>&1 &

sleep 2

# Query 6: Self-join without proper indexes
echo "Query 6: Self-join..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT
    n1.ID,
    n1.Value,
    n2.Value as NextValue
FROM Numbers n1
LEFT JOIN Numbers n2 ON n1.ID = n2.ID - 1
WHERE n1.ID < 1000;
" > /dev/null 2>&1 &

sleep 2

# Query 7: Aggregate with DISTINCT
echo "Query 7: Distinct aggregation..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT
    Status,
    COUNT(DISTINCT CustomerID) as UniqueCustomers,
    COUNT(OrderID) as TotalOrders,
    SUM(DISTINCT Amount) as DistinctAmounts
FROM Orders
GROUP BY Status;
" > /dev/null 2>&1 &

sleep 2

# Query 8: Window functions
echo "Query 8: Window functions..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT
    CustomerID,
    OrderID,
    Amount,
    ROW_NUMBER() OVER (PARTITION BY CustomerID ORDER BY OrderDate DESC) as RowNum,
    SUM(Amount) OVER (PARTITION BY CustomerID) as CustomerTotal,
    AVG(Amount) OVER (PARTITION BY CustomerID) as CustomerAvg
FROM Orders
WHERE CustomerID < 100;
" > /dev/null 2>&1 &

sleep 2

# Query 9: LIKE with leading wildcard (non-SARGable)
echo "Query 9: Non-SARGable LIKE query..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT * FROM Customers
WHERE Email LIKE '%@example.com'
AND LastName LIKE '%5%';
" > /dev/null 2>&1 &

sleep 2

# Query 10: Multiple ORs instead of IN
echo "Query 10: Multiple OR conditions..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
USE RelibankDB;
SELECT * FROM Orders
WHERE Status = 'Pending'
   OR Status = 'Shipped'
   OR Status = 'Delivered'
   OR CustomerID = 100
   OR CustomerID = 200
   OR Amount > 800;
" > /dev/null 2>&1 &

echo ""
echo "Waiting for queries to complete..."
wait

echo ""
echo "Step 3: Verifying queries are in plan cache..."
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT
    COUNT(*) as CachedQueryCount,
    SUM(execution_count) as TotalExecutions
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
WHERE st.text NOT LIKE '%sys.%'
AND st.text NOT LIKE '%INFORMATION_SCHEMA%';
"

echo ""
echo "Load generation complete!"
echo "New Relic should now be able to collect execution plans from these queries."
echo ""
echo "To generate continuous load, run this script periodically or in a loop."

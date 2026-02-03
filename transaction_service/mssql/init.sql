-- Check if the database already exists
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'RelibankDB')
BEGIN
    CREATE DATABASE RelibankDB;
END;
GO

-- Wait until the database is truly available
DECLARE @count INT = 0;
WHILE @count < 10
BEGIN
    IF EXISTS (SELECT * FROM sys.databases WHERE name = 'RelibankDB' AND state_desc = 'ONLINE')
    BEGIN
        BREAK;
    END
    WAITFOR DELAY '00:00:02';
    SET @count = @count + 1;
END;
GO

-- ==============================================================================
-- NEW RELIC MONITORING SETUP - SERVER LEVEL
-- ==============================================================================

-- Create New Relic login and user if it doesn't exist
USE master;
GO

IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'newrelic')
BEGIN
    CREATE LOGIN newrelic WITH PASSWORD = 'YourStrong@Password!';
    PRINT 'Created New Relic login';
END
ELSE
BEGIN
    PRINT 'New Relic login already exists, skipping creation';
END;
GO

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'newrelic')
BEGIN
    CREATE USER newrelic FOR LOGIN newrelic;
    PRINT 'Created New Relic user in master';
END;
GO

-- Grant server-level permissions to newrelic user
IF EXISTS (SELECT * FROM sys.server_principals WHERE name = 'newrelic')
BEGIN
    -- These GRANT statements are idempotent - they won't error if already granted
    GRANT CONNECT SQL TO newrelic;
    GRANT VIEW SERVER STATE TO newrelic;  -- Required for DMVs (sys.dm_exec_*)
    GRANT VIEW ANY DEFINITION TO newrelic;  -- Required for execution plans
    PRINT 'Granted server-level permissions to New Relic user';
END;
GO

-- Disable 'optimize for ad hoc workloads' setting
-- This ensures that query plans are cached immediately instead of only storing stubs
DECLARE @adhoc_current INT;
SELECT @adhoc_current = CONVERT(INT, value_in_use)
FROM sys.configurations
WHERE name = 'optimize for ad hoc workloads';

IF @adhoc_current = 1
BEGIN
    PRINT 'Disabling ad hoc workload optimization for better monitoring...';
    EXEC sp_configure 'show advanced options', 1;
    RECONFIGURE;
    EXEC sp_configure 'optimize for ad hoc workloads', 0;
    RECONFIGURE;
    PRINT 'Ad hoc optimization disabled';
END
ELSE
BEGIN
    PRINT 'Ad hoc optimization already disabled';
END;
GO

-- ==============================================================================
-- DATABASE SETUP - RELIBANK
-- ==============================================================================

-- Switch to the new database
USE RelibankDB;
GO

-- Create the Transactions table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Transactions' and xtype='U')
BEGIN
    CREATE TABLE Transactions (
        TransactionID INT IDENTITY(1,1) PRIMARY KEY,
        EventType VARCHAR(50) NOT NULL,
        BillID VARCHAR(50) NOT NULL,
        Amount DECIMAL(19, 4) NOT NULL,
        Currency VARCHAR(10) NOT NULL,
        AccountID INT NOT NULL,
        Timestamp FLOAT NOT NULL,
        StartDate DATE,
        CancellationUserID VARCHAR(50),
        CancellationTimestamp FLOAT
    );
    PRINT 'Created Transactions table';
END;
GO

-- Create the new Ledger table for double-entry accounting
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Ledger' and xtype='U')
BEGIN
    CREATE TABLE Ledger (
        AccountID INT PRIMARY KEY,
        CurrentBalance DECIMAL(19, 4) NOT NULL
    );
    PRINT 'Created Ledger table';
END;
GO

-- Insert initial balances into the Ledger table
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 12345)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (12345, 1500.50);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 56789)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (56789, 5000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 98765)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (98765, 1200.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 67890)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (67890, 750.25);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10111)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10111, 5000.00);
END;

-- Additional user accounts
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10001)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10001, 2500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10002)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10002, 8750.50);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10003)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10003, 1200.75);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10004)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10004, 3400.25);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10005)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10005, 15000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10006)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10006, 950.50);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10007)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10007, 6200.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10008)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10008, 5800.75);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10009)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10009, 1100.25);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10010)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10010, 450.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10011)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10011, 9500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10012)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10012, 12000.50);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10013)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10013, 3700.75);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10014)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10014, 11200.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 10015)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (10015, 8900.25);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20001)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20001, 15000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20002)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20002, 25000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20003)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20003, 50000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20004)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20004, 18000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20005)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20005, 30000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20006)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20006, 40000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20007)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20007, 35000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20008)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20008, 28000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20009)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20009, 22000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 20010)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (20010, 19000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30001)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30001, 5000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30002)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30002, 3000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30003)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30003, 2000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30004)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30004, 4000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30005)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30005, 1500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30006)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30006, 1000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30007)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30007, 3500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30008)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30008, 6000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30009)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30009, 4500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30010)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30010, 2500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30011)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30011, 3500.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30012)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30012, 5000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30013)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30013, 2000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30014)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30014, 4000.00);
END;
IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountID = 30015)
BEGIN
    INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (30015, 3000.00);
END;

-- Create a new table to store recurring payment schedules
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='RecurringSchedules' and xtype='U')
BEGIN
    CREATE TABLE RecurringSchedules (
        ScheduleID INT IDENTITY(1,1) PRIMARY KEY,
        BillID VARCHAR(50) NOT NULL,
        Amount DECIMAL(19, 4) NOT NULL,
        Currency VARCHAR(10) NOT NULL,
        AccountID INT NOT NULL,
        Frequency VARCHAR(50) NOT NULL,
        StartDate DATE NOT NULL,
        Timestamp FLOAT NOT NULL
    );
    PRINT 'Created RecurringSchedules table';
END;
GO

-- ==============================================================================
-- NEW RELIC MONITORING SETUP - DATABASE LEVEL
-- ==============================================================================

-- Create newrelic user in RelibankDB and grant permissions
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'newrelic')
BEGIN
    CREATE USER newrelic FOR LOGIN newrelic;
    PRINT 'Created New Relic user in RelibankDB';
END;
GO

-- Grant database-level permissions (these are idempotent)
IF EXISTS (SELECT * FROM sys.database_principals WHERE name = 'newrelic')
BEGIN
    ALTER ROLE db_datareader ADD MEMBER newrelic;
    GRANT VIEW DATABASE PERFORMANCE STATE TO newrelic;  -- Required for Query Store
    GRANT VIEW DATABASE STATE TO newrelic;  -- Required for Query Store
    PRINT 'Granted database-level permissions to New Relic user';
END;
GO

-- Enable Query Store for New Relic query monitoring
DECLARE @qs_enabled BIT;
SELECT @qs_enabled = CONVERT(BIT, is_query_store_on)
FROM sys.databases
WHERE name = 'RelibankDB';

IF @qs_enabled = 0 OR @qs_enabled IS NULL
BEGIN
    PRINT 'Enabling Query Store for New Relic monitoring...';
    ALTER DATABASE RelibankDB SET QUERY_STORE = ON (
        QUERY_CAPTURE_MODE = ALL,
        DATA_FLUSH_INTERVAL_SECONDS = 900
    );
    PRINT 'Query Store enabled';
END
ELSE
BEGIN
    PRINT 'Query Store already enabled';
END;
GO

-- ==============================================================================
-- INITIALIZATION COMPLETE MARKER
-- ==============================================================================

-- Create an initialization flag table to indicate setup is complete
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='InitComplete' and xtype='U')
BEGIN
    CREATE TABLE InitComplete (
        InitID INT PRIMARY KEY,
        SetupTimestamp DATETIME DEFAULT GETDATE(),
        NewRelicConfigured BIT DEFAULT 1
    );
    INSERT INTO InitComplete (InitID, NewRelicConfigured) VALUES (1, 1);
    PRINT 'Database initialization complete with New Relic monitoring configured';
END;
GO

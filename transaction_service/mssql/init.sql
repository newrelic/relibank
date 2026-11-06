-- Sync SA password from MSSQL_SA_PASSWORD env var on every run.
-- Prevents drift between the k8s secret and the SQL Server data volume
-- (SQL Server only applies MSSQL_SA_PASSWORD on first init, not restarts).
-- The password is passed in via sqlcmd -v SAPWD="..." from the init job.
USE master;
GO
ALTER LOGIN SA WITH PASSWORD = '$(SAPWD)';
GO

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

-- Use SIMPLE recovery so the transaction log self-truncates on checkpoint.
-- This is a demo/sandbox DB re-seeded on each fresh deploy; there is no log-backup
-- job, so FULL recovery caused the log (.ldf) to grow without bound and fill the
-- data volume, stalling the server with 1105/1101 allocation errors. Idempotent.
ALTER DATABASE RelibankDB SET RECOVERY SIMPLE;
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
    GRANT VIEW ANY DATABASE TO newrelic;  -- Required for NRDOT database discovery
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

-- Add Status and DeclineReason columns to Transactions table if they don't exist
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Transactions') AND name = 'Status')
BEGIN
    ALTER TABLE Transactions ADD Status VARCHAR(20) NULL;
    PRINT 'Added Status column to Transactions table';
END;
GO

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Transactions') AND name = 'DeclineReason')
BEGIN
    ALTER TABLE Transactions ADD DeclineReason VARCHAR(500) NULL;
    PRINT 'Added DeclineReason column to Transactions table';
END;
GO

-- Add Direction column to Transactions table if it doesn't exist.
-- 'D' = debit (decreases Ledger.CurrentBalance), 'C' = credit (increases it), NULL = not
-- a ledger-affecting event (declined payments, AccountID=0 card payments). Set by the
-- Kafka consumer at write time so sp_RebuildAccountLedgerBalance can recompute balances
-- without re-deriving account type from accounts_service.
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('Transactions') AND name = 'Direction')
BEGIN
    ALTER TABLE Transactions ADD Direction CHAR(1) NULL;
    PRINT 'Added Direction column to Transactions table';
END;
GO

-- Backfill an InitialSeedBalance Transactions row for every Ledger account that
-- predates the Direction column, so sp_RebuildAccountLedgerBalance can reconstruct
-- each account's opening balance instead of just activity recorded since. Without
-- this, rebuilding any of the hand-seeded accounts above would wipe their opening
-- balance, since that money was inserted directly into Ledger and was never itself
-- a Transactions row. Guarded on EventType so it only ever runs once.
IF NOT EXISTS (SELECT 1 FROM Transactions WHERE EventType = 'InitialSeedBalance')
BEGIN
    INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp, Direction)
    SELECT
        'InitialSeedBalance',
        'SEED-' + CAST(AccountID AS VARCHAR(20)),
        ABS(CurrentBalance),
        'USD',
        AccountID,
        0,
        CASE WHEN CurrentBalance >= 0 THEN 'C' ELSE 'D' END
    FROM Ledger;
    PRINT 'Backfilled InitialSeedBalance Transactions for existing Ledger accounts';
END;
GO

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

-- Add LastProcessedDate column to RecurringSchedules if it doesn't exist. Tracks the
-- most recent StartDate sp_ProcessDueRecurringPayments has already posted, so the
-- scheduler's 1-minute poll loop doesn't repost the same due payment every cycle.
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('RecurringSchedules') AND name = 'LastProcessedDate')
BEGIN
    ALTER TABLE RecurringSchedules ADD LastProcessedDate DATE NULL;
    PRINT 'Added LastProcessedDate column to RecurringSchedules table';
END;
GO

-- ==============================================================================
-- LOAD DATA - BANKING SEED FOR RICH EXECUTION PLANS
-- Merchants (50K) and BankTransactions (2M) provide enough rows for the
-- query optimizer to produce multi-operator execution plans with realistic
-- cardinality estimates (Hash Match, Sort, Window Spool, etc.).
-- Set-based inserts via CTE numbers tables keep init time under 60s.
-- ==============================================================================

-- Drop old demo tables if they exist from a previous schema version
DROP TABLE IF EXISTS DemoSales;
DROP TABLE IF EXISTS DemoProducts;
DROP TABLE IF EXISTS DemoEmployees;
GO

-- Merchants: 50,000 rows across 8 categories and 6 regions
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Merchants')
BEGIN
    CREATE TABLE Merchants (
        MerchantID   INT PRIMARY KEY,
        MerchantName VARCHAR(100)   NOT NULL,
        Category     VARCHAR(50)    NOT NULL,
        Region       VARCHAR(30)    NOT NULL,
        RiskTier     TINYINT        NOT NULL DEFAULT 1,
        AnnualVolume DECIMAL(14,2),
        IsActive     BIT            NOT NULL DEFAULT 1
    );
    CREATE INDEX IX_Merchants_Category ON Merchants (Category);
    CREATE INDEX IX_Merchants_Region   ON Merchants (Region);
    CREATE INDEX IX_Merchants_Risk     ON Merchants (RiskTier);

    WITH Numbers AS (
        SELECT TOP 50000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
        FROM sys.all_columns a CROSS JOIN sys.all_columns b
    )
    INSERT INTO Merchants (MerchantID, MerchantName, Category, Region, RiskTier, AnnualVolume, IsActive)
    SELECT
        n,
        'Merchant ' + CAST(n AS VARCHAR(10)),
        CASE (n % 8)
            WHEN 0 THEN 'Retail'       WHEN 1 THEN 'Restaurant' WHEN 2 THEN 'Travel'
            WHEN 3 THEN 'Healthcare'   WHEN 4 THEN 'Gas & Auto' WHEN 5 THEN 'Online'
            WHEN 6 THEN 'Grocery'      ELSE         'Entertainment'
        END,
        CASE (n % 6)
            WHEN 0 THEN 'Northeast' WHEN 1 THEN 'Southeast' WHEN 2 THEN 'Midwest'
            WHEN 3 THEN 'Southwest' WHEN 4 THEN 'West'      ELSE         'Central'
        END,
        CASE WHEN n % 20 = 0 THEN 3 WHEN n % 7 = 0 THEN 2 ELSE 1 END,
        ((n % 9000) + 1000) * 100.00,
        CASE WHEN n % 15 = 0 THEN 0 ELSE 1 END
    FROM Numbers;
    PRINT 'Created Merchants table with 50000 rows';
END;
GO

-- BankTransactions: 2,000,000 rows seeded in two 1M-row set-based batches.
-- AccountIDs 10001-20000 align with the Ledger account range.
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'BankTransactions')
BEGIN
    CREATE TABLE BankTransactions (
        TxnID      INT PRIMARY KEY,
        AccountID  INT           NOT NULL,
        MerchantID INT           NOT NULL,
        Amount     DECIMAL(10,2) NOT NULL,
        TxnDate    DATETIME      NOT NULL,
        TxnType    VARCHAR(20)   NOT NULL,
        Status     VARCHAR(15)   NOT NULL,
        Channel    VARCHAR(15)   NOT NULL
    );
    CREATE INDEX IX_BankTxn_Account  ON BankTransactions (AccountID);
    CREATE INDEX IX_BankTxn_Merchant ON BankTransactions (MerchantID);
    CREATE INDEX IX_BankTxn_Date     ON BankTransactions (TxnDate);

    -- Batch 1: rows 1-1,000,000
    WITH Numbers AS (
        SELECT TOP 1000000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
        FROM sys.all_columns a CROSS JOIN sys.all_columns b CROSS JOIN sys.all_columns c
    )
    INSERT INTO BankTransactions (TxnID, AccountID, MerchantID, Amount, TxnDate, TxnType, Status, Channel)
    SELECT
        n,
        (n % 10000) + 10001,
        (n % 50000) + 1,
        CAST(((n % 49900) + 100) AS DECIMAL(10,2)) / 100.0,
        DATEADD(SECOND, -(n * 31), GETDATE()),
        CASE (n % 4) WHEN 0 THEN 'Purchase' WHEN 1 THEN 'Refund' WHEN 2 THEN 'Transfer' ELSE 'ATM' END,
        CASE WHEN n % 50 = 0 THEN 'Flagged' WHEN n % 15 = 0 THEN 'Declined' ELSE 'Approved' END,
        CASE (n % 4) WHEN 0 THEN 'Online' WHEN 1 THEN 'InStore' WHEN 2 THEN 'Mobile' ELSE 'ATM' END
    FROM Numbers;

    -- Batch 2: rows 1,000,001-2,000,000
    WITH Numbers AS (
        SELECT TOP 1000000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) + 1000000 AS n
        FROM sys.all_columns a CROSS JOIN sys.all_columns b CROSS JOIN sys.all_columns c
    )
    INSERT INTO BankTransactions (TxnID, AccountID, MerchantID, Amount, TxnDate, TxnType, Status, Channel)
    SELECT
        n,
        (n % 10000) + 10001,
        (n % 50000) + 1,
        CAST(((n % 49900) + 100) AS DECIMAL(10,2)) / 100.0,
        DATEADD(SECOND, -(n * 31), GETDATE()),
        CASE (n % 4) WHEN 0 THEN 'Purchase' WHEN 1 THEN 'Refund' WHEN 2 THEN 'Transfer' ELSE 'ATM' END,
        CASE WHEN n % 50 = 0 THEN 'Flagged' WHEN n % 15 = 0 THEN 'Declined' ELSE 'Approved' END,
        CASE (n % 4) WHEN 0 THEN 'Online' WHEN 1 THEN 'InStore' WHEN 2 THEN 'Mobile' ELSE 'ATM' END
    FROM Numbers;
    PRINT 'Created BankTransactions table with 2000000 rows';
END;
GO

-- Update statistics after bulk inserts for accurate cardinality estimates
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'Merchants')
    UPDATE STATISTICS Merchants WITH FULLSCAN;
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'BankTransactions')
    UPDATE STATISTICS BankTransactions WITH FULLSCAN;
GO

-- ==============================================================================
-- STORED PROCEDURES (NR-635348)
-- init.sql re-runs idempotently on every pod start, so each procedure is
-- dropped and recreated rather than guarded with IF NOT EXISTS.
-- ==============================================================================

DROP PROCEDURE IF EXISTS dbo.sp_CalculateSpendingVelocity;
GO

-- Named version of the spending-velocity window-function query, previously
-- duplicated ad-hoc in transaction_service.py, run-banking-load.sh, and
-- scenario_service.py's DB360_VELOCITY_SQL. Gives NR's QPM exec-plan panel a
-- stable object to key off instead of unnamed SQL text.
CREATE PROCEDURE dbo.sp_CalculateSpendingVelocity
    @Months INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        t.TxnID,
        t.AccountID,
        t.MerchantID,
        m.Category,
        m.Region,
        m.RiskTier,
        t.Amount,
        t.TxnDate,
        t.TxnType,
        t.Channel,
        ROW_NUMBER()  OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate)
                                                        AS TxnSeq,
        SUM(t.Amount) OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                                        AS CumulativeSpend,
        AVG(t.Amount) OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate
                            ROWS BETWEEN 99 PRECEDING AND CURRENT ROW)
                                                        AS MovingAvg100,
        RANK()        OVER (PARTITION BY m.Category ORDER BY t.Amount DESC)
                                                        AS GlobalAmountRank
    FROM BankTransactions t WITH (INDEX(0))
    INNER JOIN Merchants m WITH (INDEX(0)) ON m.MerchantID = t.MerchantID
    WHERE t.TxnDate >= DATEADD(MONTH, -@Months, GETDATE())
    ORDER BY t.AccountID, t.TxnDate
    OPTION (MAXDOP 1);
END;
GO

DROP PROCEDURE IF EXISTS dbo.sp_ProcessDueRecurringPayments;
GO

-- Posts due RecurringSchedules rows: one Transactions insert + one Ledger
-- upsert per schedule, in a single transaction. Fills the gap where
-- scheduler_service.py previously only sent a Kafka notification and never
-- actually moved money. LastProcessedDate makes this idempotent against the
-- scheduler's 1-minute poll loop re-running against the same due date.
CREATE PROCEDURE dbo.sp_ProcessDueRecurringPayments
    @ProcessDate DATE
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Processed TABLE (
        ScheduleID INT,
        BillID     VARCHAR(50),
        AccountID  INT,
        Amount     DECIMAL(19, 4),
        Currency   VARCHAR(10)
    );

    DECLARE @ScheduleID INT, @BillID VARCHAR(50), @AccountID INT,
            @Amount DECIMAL(19, 4), @Currency VARCHAR(10);

    DECLARE due_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT ScheduleID, BillID, AccountID, Amount, Currency
        FROM RecurringSchedules
        WHERE StartDate = @ProcessDate
          AND (LastProcessedDate IS NULL OR LastProcessedDate <> @ProcessDate);

    OPEN due_cursor;
    FETCH NEXT FROM due_cursor INTO @ScheduleID, @BillID, @AccountID, @Amount, @Currency;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            BEGIN TRANSACTION;

            INSERT INTO Transactions (EventType, BillID, Amount, Currency, AccountID, Timestamp, Direction)
            VALUES ('RecurringPaymentProcessed', @BillID, @Amount, @Currency, @AccountID,
                    DATEDIFF(SECOND, '1970-01-01', SYSUTCDATETIME()), 'D');

            UPDATE Ledger SET CurrentBalance = CurrentBalance - @Amount WHERE AccountID = @AccountID;
            IF @@ROWCOUNT = 0
                INSERT INTO Ledger (AccountID, CurrentBalance) VALUES (@AccountID, -@Amount);

            UPDATE RecurringSchedules SET LastProcessedDate = @ProcessDate WHERE ScheduleID = @ScheduleID;

            INSERT INTO @Processed (ScheduleID, BillID, AccountID, Amount, Currency)
            VALUES (@ScheduleID, @BillID, @AccountID, @Amount, @Currency);

            COMMIT TRANSACTION;
        END TRY
        BEGIN CATCH
            IF XACT_STATE() <> 0
                ROLLBACK TRANSACTION;
        END CATCH;

        FETCH NEXT FROM due_cursor INTO @ScheduleID, @BillID, @AccountID, @Amount, @Currency;
    END;

    CLOSE due_cursor;
    DEALLOCATE due_cursor;

    SELECT ScheduleID, BillID, AccountID, Amount, Currency FROM @Processed;
END;
GO

DROP PROCEDURE IF EXISTS dbo.sp_RebuildAccountLedgerBalance;
GO

-- Recomputes Ledger.CurrentBalance from the signed Transactions.Direction
-- history (set by the Kafka consumer at write time) for one account, or all
-- accounts when @AccountID is NULL. Only Transactions is a source of truth
-- for a given account's balance; BankTransactions is unrelated bulk load-gen
-- data whose AccountID range barely overlaps the seeded Ledger accounts.
CREATE PROCEDURE dbo.sp_RebuildAccountLedgerBalance
    @AccountID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Recalculated TABLE (
        AccountID            INT PRIMARY KEY,
        RecalculatedBalance  DECIMAL(19, 4)
    );

    INSERT INTO @Recalculated (AccountID, RecalculatedBalance)
    SELECT
        AccountID,
        SUM(CASE WHEN Direction = 'C' THEN Amount
                 WHEN Direction = 'D' THEN -Amount
                 ELSE 0 END)
    FROM Transactions
    WHERE Direction IS NOT NULL
      AND (@AccountID IS NULL OR AccountID = @AccountID)
    GROUP BY AccountID;

    DECLARE @Results TABLE (
        AccountID   INT,
        OldBalance  DECIMAL(19, 4),
        NewBalance  DECIMAL(19, 4),
        Delta       DECIMAL(19, 4)
    );

    INSERT INTO @Results (AccountID, OldBalance, NewBalance, Delta)
    SELECT
        r.AccountID,
        ISNULL(l.CurrentBalance, 0),
        r.RecalculatedBalance,
        r.RecalculatedBalance - ISNULL(l.CurrentBalance, 0)
    FROM @Recalculated r
    LEFT JOIN Ledger l ON l.AccountID = r.AccountID;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE l
        SET l.CurrentBalance = r.RecalculatedBalance
        FROM Ledger l
        INNER JOIN @Recalculated r ON r.AccountID = l.AccountID;

        INSERT INTO Ledger (AccountID, CurrentBalance)
        SELECT r.AccountID, r.RecalculatedBalance
        FROM @Recalculated r
        WHERE NOT EXISTS (SELECT 1 FROM Ledger l WHERE l.AccountID = r.AccountID);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0
            ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT AccountID, OldBalance, NewBalance, Delta FROM @Results ORDER BY AccountID;
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

-- Enable Query Store and always enforce capture settings for New Relic query monitoring.
-- Run unconditionally so that QUERY_CAPTURE_MODE = ALL and flush interval are always correct
-- even when the DB already had QS enabled with different (e.g. AUTO) settings.
PRINT 'Configuring Query Store for New Relic monitoring...';
ALTER DATABASE RelibankDB SET QUERY_STORE = ON (
    QUERY_CAPTURE_MODE = ALL,
    DATA_FLUSH_INTERVAL_SECONDS = 60,
    WAIT_STATS_CAPTURE_MODE = ON
);
PRINT 'Query Store configured: CAPTURE_MODE=ALL, FLUSH=60s, WAIT_STATS=ON';
DECLARE @qs_enabled BIT;
SELECT @qs_enabled = CONVERT(BIT, is_query_store_on)
FROM sys.databases
WHERE name = 'RelibankDB';

IF @qs_enabled = 1
BEGIN
    PRINT 'Query Store is active';
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

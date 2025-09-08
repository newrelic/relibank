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
END;
GO

-- Create the new Ledger table for double-entry accounting
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Ledger' and xtype='U')
BEGIN
    CREATE TABLE Ledger (
        AccountID INT PRIMARY KEY,
        CurrentBalance DECIMAL(19, 4) NOT NULL
    );
END;
GO

-- Insert initial balances into the Ledger table (using integer IDs)
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

-- Create an initialization flag table to indicate setup is complete
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='InitComplete' and xtype='U')
BEGIN
    CREATE TABLE InitComplete (
        InitID INT PRIMARY KEY
    );
    INSERT INTO InitComplete VALUES (1);
END;
GO

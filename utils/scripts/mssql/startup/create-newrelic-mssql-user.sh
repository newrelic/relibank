#!/bin/bash

# Create New Relic user in MSSQL
# Run this from your local machine

echo "Creating New Relic user in MSSQL..."

kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE master;
CREATE LOGIN newrelic WITH PASSWORD = 'YourStrong@Password!';
CREATE USER newrelic FOR LOGIN newrelic;

-- Server-level permissions
GRANT CONNECT SQL TO newrelic;
GRANT VIEW SERVER STATE TO newrelic;  -- Required for DMVs (sys.dm_exec_*)
GRANT VIEW ANY DEFINITION TO newrelic;  -- Required for execution plans

-- Goes through each user database and grants READ permissions + Query Store access
DECLARE @name NVARCHAR(max)
DECLARE db_cursor CURSOR FOR
SELECT NAME
FROM master.dbo.sysdatabases
WHERE NAME NOT IN ('master','msdb','tempdb','model')
OPEN db_cursor
FETCH NEXT FROM db_cursor INTO @name WHILE @@FETCH_STATUS = 0
BEGIN
	EXECUTE('USE [' + @name + '];
		CREATE USER newrelic FOR LOGIN newrelic;
		ALTER ROLE db_datareader ADD MEMBER newrelic;
		GRANT VIEW DATABASE PERFORMANCE STATE TO newrelic;  -- Required for Query Store
		GRANT VIEW DATABASE STATE TO newrelic;  -- Required for Query Store
	');
	FETCH next FROM db_cursor INTO @name
END
CLOSE db_cursor
DEALLOCATE db_cursor
"

echo "Done! New Relic user created."

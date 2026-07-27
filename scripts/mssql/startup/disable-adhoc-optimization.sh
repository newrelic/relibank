#!/bin/bash

# Disable 'optimize for ad hoc workloads' setting
# This ensures that query plans are cached immediately in sys.dm_exec_query_stats
# instead of only storing plan stubs for ad-hoc queries

echo "Disabling 'optimize for ad hoc workloads' setting..."
echo "This ensures full plans are cached immediately (not just stubs)"
echo ""

kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
-- Show current setting
PRINT 'Current setting:';
SELECT
    name,
    value_in_use,
    CASE value_in_use
        WHEN 0 THEN 'DISABLED - All plans cached immediately (GOOD for monitoring)'
        WHEN 1 THEN 'ENABLED - Only plan stubs cached for ad-hoc queries (BAD for monitoring)'
    END AS Description
FROM sys.configurations
WHERE name = 'optimize for ad hoc workloads';
PRINT '';

-- Disable the setting
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'optimize for ad hoc workloads', 0;
RECONFIGURE;

PRINT 'Setting updated!';
PRINT '';

-- Verify the change
PRINT 'New setting:';
SELECT
    name,
    value_in_use,
    CASE value_in_use
        WHEN 0 THEN 'DISABLED - All plans cached immediately (GOOD for monitoring)'
        WHEN 1 THEN 'ENABLED - Only plan stubs cached for ad-hoc queries (BAD for monitoring)'
    END AS Description
FROM sys.configurations
WHERE name = 'optimize for ad hoc workloads';
"

echo ""
echo "Done! 'optimize for ad hoc workloads' is now disabled."
echo "Query plans will be cached immediately in sys.dm_exec_query_stats"

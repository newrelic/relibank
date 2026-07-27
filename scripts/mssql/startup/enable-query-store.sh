#!/bin/bash

# Enable Query Store on RelibankDB for New Relic Query Monitoring
# Query Store is required for New Relic to collect query performance metrics

echo "Enabling Query Store on RelibankDB..."

kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
ALTER DATABASE RelibankDB SET QUERY_STORE = ON (QUERY_CAPTURE_MODE = ALL, DATA_FLUSH_INTERVAL_SECONDS = 900);

SELECT
    name AS DatabaseName,
    is_query_store_on AS QueryStoreEnabled
FROM sys.databases
WHERE name = 'RelibankDB';
"

echo ""
echo "Query Store enabled! New Relic should now be able to collect query metrics."
echo "It may take a few minutes for query data to start appearing in New Relic."

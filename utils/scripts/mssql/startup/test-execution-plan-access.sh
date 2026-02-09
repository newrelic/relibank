#!/bin/bash

# Test if New Relic user can access execution plan DMVs

echo "Testing New Relic user access to execution plan DMVs..."
echo ""

kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
-- Test 1: Check if we can query sys.dm_exec_query_stats
SELECT TOP 5
    qs.query_hash,
    qs.execution_count,
    qs.total_elapsed_time,
    qs.plan_handle
FROM sys.dm_exec_query_stats AS qs
ORDER BY qs.last_execution_time DESC;
"

echo ""
echo "---"
echo ""

kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
-- Test 2: Check if we can get query plans
SELECT TOP 5
    qs.query_hash,
    st.text AS sql_text,
    CAST(qp.query_plan AS NVARCHAR(MAX)) AS execution_plan
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) AS qp
WHERE qs.execution_count > 0
ORDER BY qs.last_execution_time DESC;
"

echo ""
echo "If you see query results above, the newrelic user has proper access."
echo "If you see permission errors, we need to grant additional permissions."

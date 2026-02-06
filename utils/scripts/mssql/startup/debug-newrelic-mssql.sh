#!/bin/bash

echo "=========================================="
echo "New Relic MSSQL Integration Debugging"
echo "=========================================="
echo ""

# Step 1: Check if infrastructure agent pods are running
echo "Step 1: Checking Infrastructure Agent Pods..."
echo "---"
kubectl get pods -n newrelic -l app.kubernetes.io/name=newrelic-infrastructure
echo ""

# Step 2: Check if MSSQL pod is discoverable
echo "Step 2: Checking MSSQL Pod Discovery..."
echo "---"
kubectl get pods -n relibank -l app=mssql -o wide
echo ""

# Step 3: Check infrastructure agent logs for nri-mssql
echo "Step 3: Checking Infrastructure Agent Logs (last 100 lines)..."
echo "---"
kubectl logs -n newrelic -l app.kubernetes.io/name=newrelic-infrastructure --tail=100 | grep -i "mssql\|discovery\|query" || echo "No MSSQL-related logs found"
echo ""

# Step 4: Check if integration config exists
echo "Step 4: Checking if nri-mssql integration config is mounted..."
echo "---"
kubectl get configmap -n newrelic | grep -i infra || echo "No infrastructure configmaps found"
echo ""

# Step 5: Get infrastructure agent pod name
INFRA_POD=$(kubectl get pods -n newrelic -l app.kubernetes.io/name=newrelic-infrastructure -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$INFRA_POD" ]; then
    echo "ERROR: No infrastructure agent pod found!"
    echo ""
    echo "Possible issues:"
    echo "  1. Infrastructure agent not installed via Helm"
    echo "  2. Running in wrong namespace"
    echo "  3. Agent failed to start"
    echo ""
    exit 1
fi

echo "Found infrastructure agent pod: $INFRA_POD"
echo ""

# Step 6: Check if nri-mssql binary exists in the pod
echo "Step 6: Checking if nri-mssql binary exists in agent pod..."
echo "---"
kubectl exec -n newrelic $INFRA_POD -- ls -la /var/db/newrelic-infra/newrelic-integrations/bin/nri-mssql 2>/dev/null || echo "nri-mssql binary NOT FOUND in agent pod"
echo ""

# Step 7: Check integration configuration
echo "Step 7: Checking integration configuration in agent pod..."
echo "---"
kubectl exec -n newrelic $INFRA_POD -- ls -la /etc/newrelic-infra/integrations.d/ 2>/dev/null || echo "Integration config directory not found"
echo ""

# Step 8: Test MSSQL connectivity from infrastructure agent pod
echo "Step 8: Testing MSSQL connectivity from infrastructure agent pod..."
echo "---"
MSSQL_IP=$(kubectl get pod mssql-0 -n relibank -o jsonpath='{.status.podIP}')
echo "MSSQL Pod IP: $MSSQL_IP"
echo "Testing connection..."
kubectl exec -n newrelic $INFRA_POD -- sh -c "nc -zv $MSSQL_IP 1433 2>&1" || echo "Connection test failed"
echo ""

# Step 9: Check recent errors in agent
echo "Step 9: Checking for errors in agent logs..."
echo "---"
kubectl logs -n newrelic $INFRA_POD --tail=200 | grep -i "error\|fail\|warn" | tail -20 || echo "No recent errors found"
echo ""

# Step 10: Verify queries are in plan cache on MSSQL
echo "Step 10: Verifying queries in MSSQL plan cache..."
echo "---"
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT
    COUNT(*) as CachedQueries,
    SUM(execution_count) as TotalExecutions,
    MAX(last_execution_time) as LastExecution
FROM sys.dm_exec_query_stats
WHERE last_execution_time > DATEADD(MINUTE, -15, GETDATE());
"
echo ""

# Step 11: Test if newrelic user can query from agent pod
echo "Step 11: Testing newrelic user connectivity from agent pod..."
echo "---"
echo "This will attempt to connect using the newrelic user credentials..."
kubectl exec -n newrelic $INFRA_POD -- sh -c "command -v sqlcmd" 2>/dev/null && {
    echo "sqlcmd found, testing connection..."
    kubectl exec -n newrelic $INFRA_POD -- sqlcmd -S $MSSQL_IP -U newrelic -P 'YourStrong@Password!' -Q "SELECT @@VERSION" 2>&1
} || echo "sqlcmd not available in infrastructure agent pod (expected - agent uses native drivers)"
echo ""

echo "=========================================="
echo "Debugging Summary"
echo "=========================================="
echo ""
echo "Next steps based on findings:"
echo ""
echo "1. If nri-mssql binary NOT FOUND:"
echo "   → The integration isn't installed in the K8s environment"
echo "   → This is likely the issue - nri-mssql only works as a host integration"
echo ""
echo "2. If no MSSQL logs in agent:"
echo "   → Discovery might not be working"
echo "   → Check if discovery is supported in K8s for nri-mssql"
echo ""
echo "3. If connection fails:"
echo "   → Network policy or service issue"
echo "   → Check mssql service configuration"
echo ""
echo "4. If queries not in cache:"
echo "   → Need to run more queries"
echo "   → Run: bash scripts/mssql/loadgen/db-direct/generate-slow-queries.sh"
echo ""

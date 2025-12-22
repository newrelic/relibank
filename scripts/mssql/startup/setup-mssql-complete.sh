#!/bin/bash

# Complete MSSQL Setup for New Relic Monitoring
# This script runs all setup steps in the correct order

set -e

echo "==============================================="
echo "MSSQL Setup for New Relic Monitoring"
echo "==============================================="
echo ""

# Check if MSSQL pod is running
echo "1. Checking if MSSQL is running..."
if ! kubectl get pod mssql-0 -n relibank &>/dev/null; then
    echo "ERROR: MSSQL pod 'mssql-0' not found in namespace 'relibank'"
    echo "Please deploy MSSQL first with: skaffold dev"
    exit 1
fi

POD_STATUS=$(kubectl get pod mssql-0 -n relibank -o jsonpath='{.status.phase}')
if [ "$POD_STATUS" != "Running" ]; then
    echo "ERROR: MSSQL pod is not running (status: $POD_STATUS)"
    exit 1
fi

echo "✓ MSSQL pod is running"
echo ""

# Step 1: Create newrelic user
echo "2. Creating newrelic user with all required permissions..."
if [ ! -f "create-newrelic-mssql-user.sh" ]; then
    echo "ERROR: create-newrelic-mssql-user.sh not found"
    exit 1
fi
bash create-newrelic-mssql-user.sh
echo "✓ newrelic user created"
echo ""

# Step 2: Disable ad hoc optimization
echo "3. Disabling ad hoc workload optimization..."
if [ ! -f "disable-adhoc-optimization.sh" ]; then
    echo "ERROR: disable-adhoc-optimization.sh not found"
    exit 1
fi
bash disable-adhoc-optimization.sh
echo "✓ Ad hoc optimization disabled"
echo ""

# Step 3: Enable Query Store
echo "4. Enabling Query Store..."
if [ ! -f "enable-query-store.sh" ]; then
    echo "ERROR: enable-query-store.sh not found"
    exit 1
fi
bash enable-query-store.sh
echo "✓ Query Store enabled"
echo ""

# Step 4: Verify setup
echo "5. Verifying setup..."
echo ""

# Check newrelic user exists
echo "Checking newrelic user..."
USER_EXISTS=$(kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -h -1 -W -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.server_principals WHERE name = 'newrelic'" 2>/dev/null | grep -v "^$" | tail -1 | tr -d '[:space:]')
if [ "$USER_EXISTS" = "1" ]; then
    echo "  ✓ newrelic user exists"
else
    echo "  ✗ newrelic user NOT found (got: '$USER_EXISTS')"
fi

# Check ad hoc optimization
echo "Checking ad hoc optimization..."
AD_HOC=$(kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -h -1 -W -Q "SET NOCOUNT ON; SELECT value_in_use FROM sys.configurations WHERE name = 'optimize for ad hoc workloads'" 2>/dev/null | grep -v "^$" | tail -1 | tr -d '[:space:]')
if [ "$AD_HOC" = "0" ]; then
    echo "  ✓ Ad hoc optimization disabled (value: 0)"
else
    echo "  ✗ Ad hoc optimization NOT disabled (got: '$AD_HOC')"
fi

# Check Query Store
echo "Checking Query Store..."
QS_ENABLED=$(kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -h -1 -W -Q "SET NOCOUNT ON; USE RelibankDB; SELECT is_query_store_on FROM sys.databases WHERE name = 'RelibankDB'" 2>/dev/null | grep -v "^$" | tail -1 | tr -d '[:space:]')
if [ "$QS_ENABLED" = "1" ]; then
    echo "  ✓ Query Store enabled"
else
    echo "  ✗ Query Store NOT enabled (got: '$QS_ENABLED')"
fi

echo ""
echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo ""
echo "Your MSSQL database is now ready for New Relic monitoring."
echo ""
echo "Next steps:"
echo "1. Deploy New Relic monitoring:"
echo "   helm upgrade --install newrelic-bundle newrelic/nri-bundle \\"
echo "     --namespace newrelic --create-namespace \\"
echo "     --set global.licenseKey=\$NEW_RELIC_LICENSE_KEY \\"
echo "     --set global.cluster=\$CLUSTER_NAME \\"
echo "     -f scripts/mssql/nri-bundle-values.yaml"
echo ""
echo "2. (Optional) Populate DMV cache for immediate testing:"
echo "   bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh"
echo ""
echo "For troubleshooting, see: scripts/mssql/setup-mssql-for-newrelic.md"

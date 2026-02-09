# Quick Start: Setting Up MSSQL for New Relic After Cluster Restart

Follow these steps in order after restarting your cluster with Skaffold.

## Prerequisites
- Cluster is running
- Skaffold has deployed all services including MSSQL

## Step-by-Step Setup (5 minutes)

### 1. Wait for MSSQL to be Ready
```bash
kubectl wait --for=condition=ready pod/mssql-0 -n relibank --timeout=300s
```

### 2. Run Complete Setup Script
This script does everything: creates user, disables ad hoc optimization, enables Query Store.

```bash
bash scripts/mssql/startup/setup-mssql-complete.sh
```

**Expected output:**
```
✓ MSSQL pod is running
✓ newrelic user created
✓ Ad hoc optimization disabled
✓ Query Store enabled
✓ Setup verification passed
```

### 3. Deploy New Relic Monitoring

**Option A: Using nri-bundle (Recommended for production)**

```bash
# Add Helm repo (if not already added)
helm repo add newrelic https://helm-charts.newrelic.com
helm repo update
```

**Install with environment variables (recommended for keeping secrets out of version control):**
```bash
# Set your credentials
export NEW_RELIC_LICENSE_KEY="your_license_key_here"
export CLUSTER_NAME="your_cluster_name_here"

# Install nri-bundle
helm upgrade --install newrelic-bundle newrelic/nri-bundle \
  --namespace newrelic \
  --create-namespace \
  --set global.licenseKey=$NEW_RELIC_LICENSE_KEY \
  --set global.cluster=$CLUSTER_NAME \
  -f scripts/mssql/nri-bundle-values.yaml
```

**OR install with inline parameters:**
```bash
helm upgrade --install newrelic-bundle newrelic/nri-bundle \
  --namespace newrelic \
  --create-namespace \
  --set global.licenseKey=YOUR_LICENSE_KEY \
  --set global.cluster=YOUR_CLUSTER_NAME \
  -f scripts/mssql/nri-bundle-values.yaml
```

**Option B: Using standalone deployment (Simpler for testing)**
```bash
kubectl apply -f nri-mssql-deployment.yaml
```

### 4. Verify Monitoring is Working

```bash
# Check pods are running
kubectl get pods -n newrelic  # For nri-bundle
# OR
kubectl get pods -n relibank -l app=nri-mssql-monitor  # For standalone

# Check logs
kubectl logs -n newrelic -l app.kubernetes.io/component=kubelet -c agent --tail=50 | grep nri-mssql
# OR
kubectl logs -n relibank -l app=nri-mssql-monitor -c infrastructure-agent --tail=50 | grep "Sending events"
```

### 5. (Optional) Populate DMV Cache for Immediate Testing

If you want to see execution plan data immediately:

```bash
# One-time population
bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh

# OR continuous (keep running in background)
bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache-continuous.sh &
```

## Verification Checklist

After completing the steps, verify everything is working:

- [ ] MSSQL pod is running: `kubectl get pod mssql-0 -n relibank`
- [ ] newrelic user exists with permissions
- [ ] Ad hoc optimization is disabled (value = 0)
- [ ] Query Store is enabled (is_query_store_on = 1)
- [ ] New Relic agent pods are running
- [ ] Data is flowing to New Relic (check logs for "Sending events" or "Metrics post succeeded")

## Troubleshooting

### MSSQL pod not starting
```bash
kubectl describe pod mssql-0 -n relibank
kubectl logs mssql-0 -n relibank
```

### Setup script fails
- Check SA password is correct in scripts: `YourStrong@Passwor`!`
- Verify MSSQL pod is in Running state
- Check database is initialized: `kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor\`!' -C -Q "SELECT name FROM sys.databases"`

### New Relic not collecting data
1. Check agent logs for errors
2. Verify newrelic user can connect:
   ```bash
   kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "SELECT @@VERSION"
   ```
3. See detailed troubleshooting in [setup-mssql-for-newrelic.md](./setup-mssql-for-newrelic.md)

## Time Estimates
- Step 1 (Wait for MSSQL): 1-2 minutes
- Step 2 (Setup script): 1-2 minutes
- Step 3 (Deploy monitoring): 1-2 minutes
- Step 4 (Verify): 30 seconds
- Step 5 (Optional population): 2-3 minutes

**Total: ~5 minutes** (without optional DMV population)

## What Happens Automatically
- newrelic user creation
- Permission grants (server and database level)
- Ad hoc workload optimization disabled
- Query Store enabled and configured
- Verification checks

## What You Need to Monitor
- DMV cache population (volatile, cleared on restart)
- New Relic data flow (check every 5-10 minutes initially)
- Query Store data accumulation

## Files Reference
- [startup/setup-mssql-complete.sh](./startup/setup-mssql-complete.sh) - Run this first (automated setup)
- [setup-mssql-for-newrelic.md](./setup-mssql-for-newrelic.md) - Detailed documentation
- [startup/create-newrelic-mssql-user.sh](./startup/create-newrelic-mssql-user.sh) - User creation (called by complete script)
- [startup/disable-adhoc-optimization.sh](./startup/disable-adhoc-optimization.sh) - Ad hoc config (called by complete script)
- [startup/enable-query-store.sh](./startup/enable-query-store.sh) - Query Store setup (called by complete script)
- [loadgen/db-direct/populate-dmv-plan-cache.sh](./loadgen/db-direct/populate-dmv-plan-cache.sh) - Optional DMV population
- [nri-bundle-values.yaml](./nri-bundle-values.yaml) - Helm values for nri-bundle
- `../../nri-mssql-deployment.yaml` - Standalone deployment

## After Everything is Working

You should see in New Relic UI:
- Host data (infrastructure metrics)
- MSSQL instance metrics (`MSSQLInstanceSample`)
- MSSQL database metrics (`MSSQLDatabaseSample`)
- Query Store data (if populated)
- Execution plans (if DMV cache is populated and query monitoring is enabled)

Data typically appears within **5-10 minutes** of deployment.

# MSSQL Setup Guide for New Relic Monitoring

This guide prepares your MSSQL database for New Relic instrumentation after deploying with Skaffold.

## Prerequisites
- MSSQL deployed and running in Kubernetes
- SA password available
- kubectl access to the cluster

## Step-by-Step Setup

### Step 1: Create New Relic User

Run the `create-newrelic-mssql-user.sh` script to create the monitoring user with all required permissions:

```bash
bash scripts/mssql/startup/create-newrelic-mssql-user.sh
```

**What this does:**
- Creates `newrelic` login and user
- Grants server-level permissions:
  - `CONNECT SQL` - Allows connection
  - `VIEW SERVER STATE` - **Required for DMVs** (sys.dm_exec_*)
  - `VIEW ANY DEFINITION` - **Required for execution plans**
- Grants database-level permissions for all user databases:
  - `db_datareader` - Read access to tables
  - `VIEW DATABASE PERFORMANCE STATE` - **Required for Query Store**
  - `VIEW DATABASE STATE` - **Required for Query Store**

### Step 2: Disable Ad Hoc Workload Optimization

Run the `disable-adhoc-optimization.sh` script:

```bash
bash scripts/mssql/startup/disable-adhoc-optimization.sh
```

**Why this matters:**
- When **disabled (0)**: Full query plans are cached immediately in `sys.dm_exec_query_stats` ✅
- When **enabled (1)**: Only plan "stubs" are cached for ad-hoc queries ❌
- New Relic's execution plan collection requires full plans in the DMV cache

**What this does:**
- Sets `optimize for ad hoc workloads` to 0
- Verifies the setting is applied

### Step 3: Enable Query Store

Run the `enable-query-store.sh` script:

```bash
bash scripts/mssql/startup/enable-query-store.sh
```

**What this does:**
- Enables Query Store on RelibankDB
- Sets `QUERY_CAPTURE_MODE = ALL` (captures all queries)
- Sets `DATA_FLUSH_INTERVAL_SECONDS = 900` (saves to disk every 15 minutes)
- Verifies Query Store is enabled

**Why this matters:**
- Query Store provides persistent query performance history
- Survives restarts (unlike DMV cache)
- Enables advanced query performance monitoring

### Step 4: Populate DMV Plan Cache (Optional - For Testing)

To ensure execution plans show up in New Relic immediately, run one of these scripts:

**One-time population:**
```bash
bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh
```

**Continuous population (for testing):**
```bash
bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache-continuous.sh
# Press Ctrl+C to stop
```

**Why this matters:**
- The DMV plan cache (`sys.dm_exec_query_stats`) is **in-memory and volatile**
- Plans get evicted due to memory pressure, infrequent execution, or restarts
- New Relic's `MSSQLQueryExecutionPlans` feature pulls from DMV cache, NOT Query Store
- Running queries multiple times keeps them "warm" in the cache

## Verification

After completing all steps, verify the setup:

```bash
# 1. Check newrelic user exists and has permissions
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE master;
SELECT
    dp.name AS LoginName,
    dp.type_desc,
    perm.permission_name,
    perm.state_desc
FROM sys.server_principals dp
LEFT JOIN sys.server_permissions perm ON dp.principal_id = perm.grantee_principal_id
WHERE dp.name = 'newrelic';
"

# 2. Check ad hoc optimization is disabled
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT name, value_in_use
FROM sys.configurations
WHERE name = 'optimize for ad hoc workloads';
"
# Expected: value_in_use = 0

# 3. Check Query Store is enabled
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
USE RelibankDB;
SELECT name, is_query_store_on
FROM sys.databases
WHERE name = 'RelibankDB';
"
# Expected: is_query_store_on = 1

# 4. Check DMV cache has queries
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT COUNT(*) AS QueriesInCache
FROM sys.dm_exec_query_stats;
"
# Expected: > 0 (if you ran the populate script)
```

## Understanding the Monitoring Components

### DMV Plan Cache vs Query Store

| Feature | DMV Plan Cache (`sys.dm_exec_query_stats`) | Query Store (`sys.query_store_*`) |
|---------|-------------------------------------------|-----------------------------------|
| **Storage** | In-memory (RAM) | On-disk (persistent) |
| **Survives restart** | ❌ No | ✅ Yes |
| **Used by New Relic** | ✅ Yes (for execution plans) | ✅ Yes (for query metrics) |
| **Eviction** | Frequent (memory pressure) | Rare (retention policy) |
| **Population** | Automatic (when queries run) | Automatic (when queries run) |

### Required Permissions Summary

| Permission | Level | Required For | Without It |
|------------|-------|--------------|------------|
| `VIEW SERVER STATE` | Server | DMV access (execution plans) | Can't see `sys.dm_exec_*` tables |
| `VIEW ANY DEFINITION` | Server | Execution plan XML | Can't retrieve plan details |
| `VIEW DATABASE PERFORMANCE STATE` | Database | Query Store access | Can't see query performance history |
| `VIEW DATABASE STATE` | Database | Query Store metadata | Can't see Query Store configuration |
| `db_datareader` | Database | Read table data | Can't query application tables |

## Troubleshooting

### Problem: No execution plans in New Relic

**Symptom:** `MSSQLQueryExecutionPlans` event type is empty in New Relic

**Causes & Solutions:**
1. **DMV cache is empty**
   - Solution: Run `scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh` or `scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache-continuous.sh`
   - Queries need to be executed recently and frequently

2. **Missing permissions**
   - Check: `VIEW SERVER STATE` and `VIEW ANY DEFINITION` granted to newrelic user
   - Solution: Re-run `scripts/mssql/startup/create-newrelic-mssql-user.sh`

3. **Ad hoc optimization enabled**
   - Check: `optimize for ad hoc workloads` = 0
   - Solution: Run `scripts/mssql/startup/disable-adhoc-optimization.sh`

4. **Integration timeout**
   - Check New Relic agent logs for "HeartBeat timeout" or "execution plan query timeout"
   - Solution: Increase `TIMEOUT` parameter in integration config (try 180 or 240)

### Problem: Query Store not capturing data

**Symptom:** `sys.query_store_query` is empty

**Causes & Solutions:**
1. **Query Store not enabled**
   - Solution: Run `scripts/mssql/startup/enable-query-store.sh`

2. **Query Store in read-only mode**
   ```sql
   SELECT actual_state_desc FROM sys.database_query_store_options;
   ```
   - If `READ_ONLY`, increase max storage size

3. **No queries executed since enabling**
   - Solution: Run application queries or `scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh`

### Problem: Permission errors in New Relic logs

**Symptom:** Errors like "permission denied" or "cannot access sys.dm_*"

**Solution:**
1. Verify permissions:
   ```bash
   kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U newrelic -P 'YourStrong@Password!' -C -Q "
   SELECT COUNT(*) FROM sys.dm_exec_query_stats;
   "
   ```
2. If error, re-run `scripts/mssql/startup/create-newrelic-mssql-user.sh`

## Maintenance

### After Database Restart
- ✅ Query Store data: **Preserved**
- ✅ Permissions: **Preserved**
- ✅ Ad hoc optimization setting: **Preserved**
- ❌ DMV plan cache: **Cleared** - Need to re-run `scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh` or wait for queries to populate naturally

### Regular Monitoring
```bash
# Check DMV cache size
kubectl exec mssql-0 -n relibank -- /opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P 'YourStrong@Passwor`!' -C -Q "
SELECT COUNT(*) AS CachedQueries FROM sys.dm_exec_query_stats;
SELECT COUNT(*) AS QueryStoreQueries FROM RelibankDB.sys.query_store_query;
"
```

## Quick Reference Commands

```bash
# Create newrelic user with all permissions
bash scripts/mssql/startup/create-newrelic-mssql-user.sh

# Disable ad hoc optimization (required for plan caching)
bash scripts/mssql/startup/disable-adhoc-optimization.sh

# Enable Query Store
bash scripts/mssql/startup/enable-query-store.sh

# Populate DMV cache (for immediate testing)
bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache.sh

# Continuous cache population (keep running in background)
bash scripts/mssql/loadgen/db-direct/populate-dmv-plan-cache-continuous.sh &
```

## Notes

- All scripts use SA password: `YourStrong@Passwor`!` (note the backtick before the exclamation)
- Scripts assume MSSQL pod is named `mssql-0` in namespace `relibank`
- New Relic user password: `YourStrong@Password!`
- Query monitoring has a performance impact - monitor database CPU/memory usage

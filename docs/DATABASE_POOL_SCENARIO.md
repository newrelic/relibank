# Database Pool Performance Scenario

## Overview

This scenario simulates a situation where users on a specific database pool (pool-a or pool-b) experience performance degradation due to connection pool issues. This demonstrates how to identify and diagnose performance problems that affect a subset of users sharing the same infrastructure.

## Architecture

### User Assignment to Pools

Users are deterministically assigned to either **pool-a** or **pool-b** based on their user_id:

```python
def assign_user_to_pool(user_id: str) -> str:
    """Uses MD5 hash for consistent pool assignment"""
    user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return "pool-a" if (user_hash % 2) == 0 else "pool-b"
```

**Key characteristics:**
- ~50% of users assigned to each pool
- Same user always gets same pool (deterministic)
- Pool assignment is transparent to the user

### How the Scenario Works

When enabled, the scenario introduces artificial delay for database connections used by the affected pool:

1. User makes request to accounts service
2. Accounts service determines user's pool assignment
3. If scenario is enabled and user is on affected pool:
   - Connection is held for configured delay (default 500ms)
   - This simulates connection pool contention/exhaustion
4. New Relic custom attributes track the performance impact

## Configuration

### Enable via API

**Enable pool stress for pool-a:**
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/ab-testing/db-pool-stress?enabled=true&delay_ms=500&affected_pool=pool-a"
```

**Enable pool stress for pool-b:**
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/ab-testing/db-pool-stress?enabled=true&delay_ms=1000&affected_pool=pool-b"
```

**Disable:**
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/ab-testing/db-pool-stress?enabled=false"
```

**Check current config:**
```bash
curl "http://localhost:8000/scenario-runner/api/ab-testing/config"
```

### Enable via UI

1. Navigate to Scenario Runner UI: `http://localhost:8000/scenario-runner/home`
2. Find "Database Pool Performance Issue" in the A/B Testing section
3. Click the toggle button to enable/disable

### Parameters

- `enabled` (boolean): Enable/disable the scenario
- `delay_ms` (integer): How long to hold each connection in milliseconds (0-10000)
- `affected_pool` (string): Which pool experiences issues ("pool-a" or "pool-b")

## New Relic Observability

### Custom Attributes

The accounts service adds the following custom attributes to transactions:

| Attribute | Type | Description |
|-----------|------|-------------|
| `db.pool_id` | string | Which pool the user is assigned to (pool-a, pool-b, unknown) |
| `db.pool_wait_time_ms` | integer | Time spent waiting for database connection |
| `db.pool_exhausted` | boolean | Whether the connection pool was exhausted |

### NRQL Queries for Analysis

#### 1. Compare Performance by Pool

```sql
SELECT
  average(duration) as 'Avg Response Time (s)',
  percentile(duration, 50, 95, 99) as 'Response Time Percentiles',
  count(*) as 'Request Count'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_id IS NOT NULL
FACET db.pool_id
SINCE 30 minutes ago
```

**Expected Results:**
- Normal: Both pools show similar response times
- With scenario: Affected pool shows higher response times

#### 2. Identify Affected Users

```sql
SELECT
  enduser.id as 'User ID',
  db.pool_id as 'Pool',
  average(duration) as 'Avg Response Time',
  count(*) as 'Requests'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_id IS NOT NULL
FACET enduser.id, db.pool_id
SINCE 30 minutes ago
ORDER BY average(duration) DESC
LIMIT 20
```

**Expected Results:**
- Shows which specific users are experiencing slow performance
- Reveals that slow users are all on the same pool

#### 3. Pool Wait Time Analysis

```sql
SELECT
  average(db.pool_wait_time_ms) as 'Avg Wait Time (ms)',
  max(db.pool_wait_time_ms) as 'Max Wait Time (ms)',
  count(*) as 'Requests'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_wait_time_ms IS NOT NULL
FACET db.pool_id
SINCE 30 minutes ago
```

**Expected Results:**
- Shows connection acquisition time by pool
- Affected pool shows higher wait times

#### 4. Pool Exhaustion Incidents

```sql
SELECT
  count(*) as 'Exhaustion Events',
  db.pool_id as 'Pool'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_exhausted = true
FACET db.pool_id
TIMESERIES
SINCE 1 hour ago
```

**Expected Results:**
- Shows when and how often pool exhaustion occurred
- Should only show events for affected pool

#### 5. Performance Trend Over Time

```sql
SELECT
  percentile(duration, 95) as 'P95 Response Time'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_id IS NOT NULL
FACET db.pool_id
TIMESERIES AUTO
SINCE 1 hour ago
```

**Expected Results:**
- Clear divergence when scenario is enabled
- Both pools return to similar performance when disabled

#### 6. Error Rate by Pool

```sql
SELECT
  percentage(count(*), WHERE error = true) as 'Error Rate (%)'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_id IS NOT NULL
FACET db.pool_id
TIMESERIES
SINCE 30 minutes ago
```

**Expected Results:**
- Affected pool may show higher error rates if pool exhaustion occurs

## Demo Workflow

### Scenario: Customer Complaints Investigation

**Step 1: Initial Reports**
- "Some users report slow account loading"
- "Response times are inconsistent"

**Step 2: Enable the Scenario**
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/ab-testing/db-pool-stress?enabled=true&delay_ms=500&affected_pool=pool-a"
```

**Step 3: Generate Load**
- Open ReliBank frontend: `http://localhost:3000`
- Log in with multiple test users
- Navigate to dashboard/accounts page

**Step 4: Query New Relic**

Run the "Compare Performance by Pool" query:
```sql
SELECT
  average(duration) as 'Avg Response Time (s)',
  percentile(duration, 95) as 'P95 Response Time',
  count(*) as 'Requests'
FROM Transaction
WHERE appName = 'Reli - Accounts Service'
  AND db.pool_id IS NOT NULL
FACET db.pool_id
SINCE 10 minutes ago
```

**Step 5: Identify Root Cause**
- Notice pool-a shows significantly higher response times
- Run "Identify Affected Users" query to see which users are impacted
- Confirm all slow users are on pool-a

**Step 6: Resolution**
```bash
curl -X POST "http://localhost:8000/scenario-runner/api/ab-testing/db-pool-stress?enabled=false"
```

**Step 7: Verify Fix**
- Re-run performance queries
- Confirm both pools now show similar response times

## Testing

### Unit Tests

Run the scenario API unit tests:

```bash
source .venv-test/bin/activate
pytest tests/test_db_pool_scenarios.py -v -s
```

**Test coverage:**
- Service health check
- User pool assignment verification
- Enable/disable scenarios
- Pool validation (pool-a, pool-b)
- Delay validation (0-10000ms)
- Reset functionality

### End-to-End Test

Run the full E2E test with New Relic validation:

```bash
export NEW_RELIC_USER_API_KEY=<your-key>
source .venv-test/bin/activate
pytest tests/test_db_pool_e2e.py -v -s
```

**E2E test steps:**
1. Enables scenario via API
2. Verifies configuration
3. Generates traffic to both pools
4. Waits for New Relic data
5. Validates custom attributes in New Relic
6. Validates performance difference between pools

## Files Modified

| File | Changes |
|------|---------|
| `scenario_service/scenario_service.py` | Added `db_pool_stress_*` fields to `AB_TEST_SCENARIOS`, added `/api/ab-testing/db-pool-stress` endpoint |
| `accounts_service/accounts_service.py` | Added `assign_user_to_pool()`, `get_db_connection_with_pool_tracking()`, added New Relic custom attributes |
| `scenario_service/index.html` | Added UI toggle for database pool stress scenario |
| `tests/test_db_pool_scenarios.py` | Created unit test suite for scenario API |
| `tests/test_db_pool_e2e.py` | Created E2E test with New Relic validation |

## Troubleshooting

### Scenario not taking effect

1. **Check scenario is enabled:**
   ```bash
   curl "http://localhost:8000/scenario-runner/api/ab-testing/config"
   ```

2. **Verify user's pool assignment:**
   - Use NRQL query to check `db.pool_id` attribute
   - Ensure user is on the affected pool

3. **Check service logs:**
   ```bash
   # Look for pool assignment logs
   kubectl logs -l app=accounts-service -n relibank | grep "DB Pool"
   ```

### Custom attributes not appearing in New Relic

1. **Verify New Relic agent is initialized:**
   - Check application is started with `newrelic-admin run-program`

2. **Check attribute naming:**
   - Attributes appear as `db.pool_id`, `db.pool_wait_time_ms`, `db.pool_exhausted`
   - Do NOT query for `custom.db.pool_id` - the `custom.` prefix is not added

3. **Ensure transactions are completing:**
   - Custom attributes only sent on transaction completion

4. **Check environment variables:**
   - `NEW_RELIC_LICENSE_KEY` must be set
   - `NEW_RELIC_APP_NAME` should be "Reli - Accounts Service"

## Best Practices

1. **Use realistic delays:** 500-1000ms is typical for connection pool contention
2. **Monitor during scenario:** Watch New Relic for unexpected behavior
3. **Reset after demo:** Always disable scenario when done
4. **Test with multiple users:** Need activity on both pools to see contrast
5. **Create deployment markers:** Mark when scenario is enabled/disabled for clear analysis

## Related Documentation

- [A/B Testing LCP Scenario](../CLAUDE.md#relibank-lcp-ab-test-scenario-implementation-plan)
- [Payment Scenarios](../scenario_service/README.md)
- [New Relic Python Agent Documentation](https://docs.newrelic.com/docs/apm/agents/python-agent/)

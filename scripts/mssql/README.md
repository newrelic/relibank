# MSSQL Scripts & Documentation

All MSSQL-related scripts and documentation for database initialization, configuration, monitoring setup, and load generation.

## Getting Started

- **New to MSSQL setup?** Start with [QUICKSTART.md](./QUICKSTART.md) for a 5-minute setup guide
- **Need detailed information?** See [setup-mssql-for-newrelic.md](./setup-mssql-for-newrelic.md) for comprehensive documentation

## Directory Structure

```
scripts/mssql/
├── README.md (this file)
├── QUICKSTART.md              - Quick 5-minute setup guide
├── setup-mssql-for-newrelic.md - Detailed monitoring setup documentation
├── nri-bundle-values.yaml     - Helm values for New Relic nri-bundle
├── startup/                    - Database initialization and setup scripts
└── loadgen/                    - Load generation and testing scripts
```

## Startup Scripts (`startup/`)

These scripts are for initial database setup, configuration, and monitoring setup:

- **`setup-mssql-complete.sh`** - Orchestrator script that runs all setup steps
- **`create-newrelic-mssql-user.sh`** - Creates New Relic monitoring user with required permissions
- **`enable-query-store.sh`** - Enables Query Store for persistent query metrics
- **`disable-adhoc-optimization.sh`** - Disables ad hoc optimization for better query plan caching
- **`test-execution-plan-access.sh`** - Tests access to execution plans and DMVs
- **`debug-newrelic-mssql.sh`** - Debug tool for troubleshooting New Relic monitoring

**Usage Example (run from repo root):**
```bash
# Run complete setup after deploying MSSQL
bash scripts/mssql/startup/setup-mssql-complete.sh

# Or run individual scripts
bash scripts/mssql/startup/create-newrelic-mssql-user.sh
bash scripts/mssql/startup/disable-adhoc-optimization.sh
bash scripts/mssql/startup/enable-query-store.sh
```

## LoadGen Scripts (`loadgen/`)

These scripts generate load and test scenarios for the MSSQL database:

- **`populate-dmv-plan-cache.sh`** - One-time population of DMV plan cache with various queries
- **`populate-dmv-plan-cache-continuous.sh`** - Continuous cache population (runs every 30s)
- **`generate-slow-queries.sh`** - Generates intentionally slow queries for testing monitoring
- **`generate-query-load.sh`** - Generates realistic query load patterns
- **`create-mssql-blocking.sh`** - Creates blocking scenarios for testing lock detection

**Usage Example (run from repo root):**
```bash
# Generate load for testing
bash scripts/mssql/loadgen/generate-slow-queries.sh

# Or keep cache warm continuously
bash scripts/mssql/loadgen/populate-dmv-plan-cache-continuous.sh &

# Create blocking scenario
bash scripts/mssql/loadgen/create-mssql-blocking.sh
```

## Quick Start

**All commands assume you're in the repository root directory.**

### After Deploying MSSQL

1. **Run setup** (one-time):
   ```bash
   bash scripts/mssql/startup/setup-mssql-complete.sh
   ```

2. **Generate load** (optional, for testing):
   ```bash
   bash scripts/mssql/loadgen/populate-dmv-plan-cache.sh
   ```

### For Continuous Testing

Keep DMV cache populated for monitoring:
```bash
bash scripts/mssql/loadgen/populate-dmv-plan-cache-continuous.sh &
```

Generate slow queries for monitoring demos:
```bash
while true; do bash scripts/mssql/loadgen/generate-slow-queries.sh; sleep 30; done
```

## Best Practices

1. **Startup scripts** should be idempotent (safe to run multiple times)
2. **LoadGen scripts** should be interruptible (safe to Ctrl+C)
3. All scripts assume kubectl access to the `relibank` namespace
4. Default MSSQL pod name: `mssql-0`
5. Default SA password: `YourStrong@Passwor\`!`
6. Run all commands from the repository root directory

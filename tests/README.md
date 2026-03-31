# Relibank Test Suite

This directory contains a comprehensive test suite for the Relibank application, including end-to-end tests, scenario service API tests (payment, chaos, and load testing scenarios), and payment behavior tests.

## 🚀 Quick Start

**New to the test suite?** See [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide.

**TL;DR:**
```bash
# Setup (one time)
cd tests
./setup_test_env.sh

# Run tests locally
./run_tests.sh

# Run tests against remote
export RELIBANK_URL="http://your-server.example.com"
./run_tests.sh -e remote
```

---

## Test Files Overview

| Test File | Purpose | Key Features |
|-----------|---------|--------------|
| `test_end_to_end.py` | End-to-end microservice tests | Frontend, accounts service, bill pay service, support service, complete user flows |
| `test_browser_user_tracking.py` | Browser user ID tracking tests | Random assignment, header override, UUID validation, consistency |
| `test_apm_user_tracking.py` | APM user ID header propagation tests | Header acceptance, multi-service chains, concurrent requests |
| `test_scenario_service.py` | Scenario service API tests | Payment scenarios, chaos scenarios, locust load testing - all via API |
| `test_payment_scenarios.py` | Payment failure scenarios | Gateway timeout, card decline, stolen card with probabilities |
| `test_rogue_deployment_scenarios.py` | Rogue AI agent deployment tests | Agent switching (gpt-4o vs gpt-4o-mini), decline rate comparison, runtime configuration |
| `test_ab_testing_scenarios.py` | A/B testing scenarios | LCP slowness (percentage-based and cohort-based), 11 hardcoded test users, cohort assignment, deterministic distribution |
| `test_stress_scenarios.py` | Stress chaos experiments | CPU stress, memory stress, combined stress testing with Chaos Mesh |
| `../frontend_service/app/**/*.test.tsx` | Frontend functional tests (Vitest) | Login, transfers, bill payment (Stripe), support, form validation, API integration |

## Prerequisites

### 1. Services Running

For **local testing**, ensure the Relibank stack is running:
```bash
skaffold dev
```

For **remote testing**, ensure you have access to the deployed environment and URLs.

### 2. Python Dependencies

Install required packages:
```bash
# Python test dependencies
pip install pytest requests

# Frontend test dependencies (from frontend_service directory)
cd ../frontend_service
npm install
```

### 3. Service Availability

Verify services are accessible:
- **Local**:
  - Frontend: http://localhost:3000
  - Accounts Service: http://localhost:5002
  - Bill Pay Service: http://localhost:5000
  - Support Service: http://localhost:5003
- **Remote**: Set via environment variables (see below)

## Running the Tests

### Run All Tests

```bash
# Run all tests in the suite (Python + Frontend)
./run_tests.sh

# Run specific test file
pytest tests/test_end_to_end.py -v -s

# Run only frontend tests
./run_tests.sh -t frontend
```

**Expected Results**:
```
tests/test_end_to_end.py::test_frontend_loads PASSED
tests/test_end_to_end.py::test_accounts_service_health PASSED
tests/test_end_to_end.py::test_bill_pay_service_health PASSED
tests/test_end_to_end.py::test_support_service_health PASSED
tests/test_end_to_end.py::test_create_user_account PASSED
tests/test_end_to_end.py::test_get_user_account PASSED
tests/test_end_to_end.py::test_create_bank_account PASSED
tests/test_end_to_end.py::test_get_bank_accounts PASSED
tests/test_end_to_end.py::test_support_interaction PASSED
tests/test_end_to_end.py::test_bill_payment_flow PASSED
tests/test_end_to_end.py::test_complete_user_journey PASSED
```

### Run Individual Tests

```bash
# End-to-end tests
pytest tests/test_end_to_end.py::test_complete_user_journey -v -s
pytest tests/test_end_to_end.py::test_bill_payment_flow -v -s
pytest tests/test_end_to_end.py::test_support_interaction -v -s

# User tracking tests (NEW)
pytest tests/test_browser_user_tracking.py -v -s
pytest tests/test_apm_user_tracking.py -v -s

# Scenario service tests (payment, chaos, locust)
pytest tests/test_scenario_service.py::test_enable_gateway_timeout -v -s
pytest tests/test_scenario_service.py::test_reset_all_scenarios -v -s
pytest tests/test_scenario_service.py::test_chaos_scenarios_api -v -s
pytest tests/test_scenario_service.py::test_locust_start_stop -v -s

# Payment scenario tests
pytest tests/test_payment_scenarios.py::test_gateway_timeout_scenario -v -s
pytest tests/test_payment_scenarios.py::test_realistic_probability_distribution -v -s

# Stress chaos tests
pytest tests/test_stress_scenarios.py::test_trigger_cpu_stress -v -s
pytest tests/test_stress_scenarios.py::test_trigger_memory_stress -v -s
pytest tests/test_stress_scenarios.py::test_service_health_during_stress -v -s

# Frontend tests
./run_tests.sh -t frontend
# Or directly: cd ../frontend_service && npm test
```

## What's Tested

**Python Backend Tests (pytest)**:
- **test_end_to_end.py**: 11 tests - Service health checks, user/account creation, bill payment, support, complete user journeys
- **test_browser_user_tracking.py**: 7 tests - Browser user ID assignment, header override, UUID validation, randomness, consistency
- **test_apm_user_tracking.py**: 10 tests - APM header acceptance across services, header propagation, multi-service chains, concurrent requests
- **test_scenario_service.py**: 12+ tests - Payment scenarios API, chaos/locust endpoints, enable/disable/reset functionality
- **test_payment_scenarios.py**: 5 tests - Gateway timeout, card decline, stolen card scenarios with probability validation
- **test_stress_scenarios.py**: 7 tests - CPU/memory/combined stress chaos (requires containerd, rate limited)

**Frontend Tests (Vitest)**:
- **4 test files, 20 tests total** - Login, transfers, bill payment (Stripe), support support
- Run with: `cd frontend_service && npm test`

## Environment Variables

All tests support these environment variables for remote testing:

| Variable | Description | Default (Local) |
|----------|-------------|-----------------|
| `BASE_URL` | Base URL for frontend application | `http://localhost:3000` |
| `ACCOUNTS_SERVICE` | Accounts service API URL | `http://localhost:5002` |
| `BILL_PAY_SERVICE` | Bill pay service API URL | `http://localhost:5000` |
| `SUPPORT_SERVICE` | Chatbot service API URL | `http://localhost:5003` |

## Troubleshooting

### Services Not Accessible
```
requests.exceptions.ConnectionError: Failed to establish a new connection
```
**Solution**: Ensure services are running (`skaffold dev` for local) or verify remote URLs are correct.


### Chaos/Locust Smoke Tests Show Warning
```
⚠ Chaos scenarios not implemented (this may be normal)
⚠ Locust scenarios not implemented (this may be normal)
```
**Solution**: These features may not be implemented in all environments. The smoke tests gracefully handle missing endpoints without failing.


### Tests Fail in Remote Environment
**Solution**: Ensure environment variables are set correctly and remote services are accessible from your testing location.

## Integration with CI/CD

These tests can be added to GitHub Actions or other CI pipelines:

```yaml
- name: Run Relibank test suite
  env:
    SCENARIO_SERVICE_URL: ${{ vars.SCENARIO_SERVICE_URL }}
    BASE_URL: ${{ vars.BASE_URL }}
  run: |
    pip install pytest requests
    pytest tests/ -v --tb=short
```

## Test Coverage Summary

- ✅ **End-to-End**: Frontend load, service health checks, user/account creation, bill payment, support interaction, complete user journeys
- ✅ **User Tracking**: Browser user ID assignment (random/header-based), APM header propagation across all services, multi-service request chains
- ✅ **Scenario API**: Enable/disable/reset payment scenarios, chaos scenarios (smoke tests), locust load testing (smoke tests)
- ✅ **Payment Scenarios**: Timeout, decline, stolen card with probabilities
- ✅ **Rogue Deployment**: AI agent switching (gpt-4o vs gpt-4o-mini), decline rate comparison, runtime agent configuration via scenario service
- ✅ **A/B Testing**: LCP slowness percentage-based (affects X% of all users) and cohort-based (affects 11 hardcoded test users), deterministic cohort assignment
- ✅ **Stress Chaos**: CPU stress, memory stress, combined stress testing with Chaos Mesh, service resilience under load
- ✅ **Frontend Functional Tests**: Login flow, fund transfers, bill payment with Stripe, support support, form validation, API integration, error handling (Vitest)

## Parallel Test Execution

The test suite uses `pytest-xdist` to run tests in parallel (with `-n auto`). This speeds up test execution but requires special handling for tests that share global state.

### When Tests Need Sequential Execution

Some tests modify shared application state (like the scenario service configuration) and cannot run in parallel. These tests are run sequentially by explicitly separating them in the test workflow.

**Tests that run sequentially:**
- `test_scenario_service.py` - Scenario service API tests
- `test_payment_scenarios.py` - Payment failure scenario tests
- `test_rogue_deployment_scenarios.py` - Rogue AI agent deployment tests
- `test_ab_testing_scenarios.py` - A/B testing scenario tests

**Why sequential?** These tests all modify the scenario service's in-memory configuration state. Running them in parallel causes race conditions where tests overwrite each other's settings.

**Implementation:**
```bash
# In .github/workflows/test-suite.yml
pytest test_scenario_service.py test_payment_scenarios.py test_rogue_deployment_scenarios.py test_ab_testing_scenarios.py --tb=line --timeout=300
pytest . --ignore=test_scenario_service.py --ignore=test_payment_scenarios.py --ignore=test_rogue_deployment_scenarios.py --ignore=test_ab_testing_scenarios.py -n auto --tb=line --timeout=300
```

### Adding New Sequential Tests

When writing new tests that modify shared state:

1. **Identify the shared resource** - Does your test modify state that other tests depend on?
   - Scenario service configuration
   - Database records that aren't isolated per test
   - Global service settings

2. **Add to sequential test list** - If your test interacts with the scenario service, add it to the first pytest command in the workflow

3. **Add to ignore list** - Also add it to the `--ignore` flags in the second pytest command to prevent duplicate execution
   ```python
   @pytest.mark.xdist_group(name="database_setup")
   def test_database_migration():
       # Your test here
       ...
   ```

4. **Add cleanup** - Always reset shared state in fixtures:
   ```python
   @pytest.fixture
   def reset_scenarios():
       """Reset scenarios before and after tests"""
       requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")
       yield
       requests.post(f"{SCENARIO_SERVICE_URL}/api/payment-scenarios/reset")
   ```

### Running Tests Sequentially

To disable parallel execution entirely (useful for debugging):
```bash
# Run without xdist parallelization
pytest tests/ -v --tb=short
```

## Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Use environment variables for configuration
3. Include cleanup in fixtures or teardown
4. Add descriptive print statements for debugging
5. **Add `@pytest.mark.xdist_group` if the test modifies shared state**
6. Update this README with new test descriptions
7. Ensure tests work both locally and remotely

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
| `test_end_to_end.py` | End-to-end microservice tests | Frontend, accounts service, bill pay service, chatbot service, complete user flows |
| `test_browser_user_tracking.py` | Browser user ID tracking tests | Random assignment, header override, UUID validation, consistency |
| `test_apm_user_tracking.py` | APM user ID header propagation tests | Header acceptance, multi-service chains, concurrent requests |
| `test_scenario_service.py` | Scenario service API tests | Payment scenarios, chaos scenarios, locust load testing - all via API |
| `test_payment_scenarios.py` | Payment failure scenarios | Gateway timeout, card decline, stolen card with probabilities |
| `test_stress_scenarios.py` | Stress chaos experiments | CPU stress, memory stress, combined stress testing with Chaos Mesh |
| `../frontend_service/app/**/*.test.tsx` | Frontend functional tests (Vitest) | Login, transfers, bill payment (Stripe), chatbot, form validation, API integration |

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
  - Chatbot Service: http://localhost:5003
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
tests/test_end_to_end.py::test_chatbot_service_health PASSED
tests/test_end_to_end.py::test_create_user_account PASSED
tests/test_end_to_end.py::test_get_user_account PASSED
tests/test_end_to_end.py::test_create_bank_account PASSED
tests/test_end_to_end.py::test_get_bank_accounts PASSED
tests/test_end_to_end.py::test_chatbot_interaction PASSED
tests/test_end_to_end.py::test_bill_payment_flow PASSED
tests/test_end_to_end.py::test_complete_user_journey PASSED
```

### Run Individual Tests

```bash
# End-to-end tests
pytest tests/test_end_to_end.py::test_complete_user_journey -v -s
pytest tests/test_end_to_end.py::test_bill_payment_flow -v -s
pytest tests/test_end_to_end.py::test_chatbot_interaction -v -s

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
- **test_end_to_end.py**: 11 tests - Service health checks, user/account creation, bill payment, chatbot, complete user journeys
- **test_browser_user_tracking.py**: 7 tests - Browser user ID assignment, header override, UUID validation, randomness, consistency
- **test_apm_user_tracking.py**: 10 tests - APM header acceptance across services, header propagation, multi-service chains, concurrent requests
- **test_scenario_service.py**: 12+ tests - Payment scenarios API, chaos/locust endpoints, enable/disable/reset functionality
- **test_payment_scenarios.py**: 5 tests - Gateway timeout, card decline, stolen card scenarios with probability validation
- **test_stress_scenarios.py**: 7 tests - CPU/memory/combined stress chaos (requires containerd, rate limited)

**Frontend Tests (Vitest)**:
- **4 test files, 20 tests total** - Login, transfers, bill payment (Stripe), chatbot support
- Run with: `cd frontend_service && npm test`

## Environment Variables

All tests support these environment variables for remote testing:

| Variable | Description | Default (Local) |
|----------|-------------|-----------------|
| `BASE_URL` | Base URL for frontend application | `http://localhost:3000` |
| `ACCOUNTS_SERVICE` | Accounts service API URL | `http://localhost:5002` |
| `BILL_PAY_SERVICE` | Bill pay service API URL | `http://localhost:5000` |
| `CHATBOT_SERVICE` | Chatbot service API URL | `http://localhost:5003` |

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

- ✅ **End-to-End**: Frontend load, service health checks, user/account creation, bill payment, chatbot interaction, complete user journeys
- ✅ **User Tracking**: Browser user ID assignment (random/header-based), APM header propagation across all services, multi-service request chains
- ✅ **Scenario API**: Enable/disable/reset payment scenarios, chaos scenarios (smoke tests), locust load testing (smoke tests)
- ✅ **Payment Scenarios**: Timeout, decline, stolen card with probabilities
- ✅ **Stress Chaos**: CPU stress, memory stress, combined stress testing with Chaos Mesh, service resilience under load
- ✅ **Frontend Functional Tests**: Login flow, fund transfers, bill payment with Stripe, chatbot support, form validation, API integration, error handling (Vitest)

## Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Use environment variables for configuration
3. Include cleanup in fixtures or teardown
4. Add descriptive print statements for debugging
5. Update this README with new test descriptions
6. Ensure tests work both locally and remotely

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
| `test_scenario_service.py` | Scenario service API tests | Payment scenarios, chaos scenarios, locust load testing - all via API |
| `test_payment_scenarios.py` | Payment failure scenarios | Gateway timeout, card decline, stolen card with probabilities |
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

# Scenario service tests (payment, chaos, locust)
pytest tests/test_scenario_service.py::test_enable_gateway_timeout -v -s
pytest tests/test_scenario_service.py::test_reset_all_scenarios -v -s
pytest tests/test_scenario_service.py::test_chaos_scenarios_api -v -s
pytest tests/test_scenario_service.py::test_locust_start_stop -v -s

# Payment scenario tests
pytest tests/test_payment_scenarios.py::test_gateway_timeout_scenario -v -s
pytest tests/test_payment_scenarios.py::test_realistic_probability_distribution -v -s

# Frontend tests
./run_tests.sh -t frontend
# Or directly: cd ../frontend_service && npm test
```

## Test Descriptions

### test_end_to_end.py - End-to-End Microservice Tests

Tests complete user workflows across all Relibank microservices: frontend, accounts service, bill pay service, and chatbot service.

**Key Tests**:
- `test_frontend_loads` - Verify React frontend is accessible
- `test_accounts_service_health` - Verify accounts service health
- `test_bill_pay_service_health` - Verify bill pay service health
- `test_chatbot_service_health` - Verify chatbot service health
- `test_create_user_account` - Test user account creation
- `test_get_user_account` - Test retrieving user information
- `test_create_bank_account` - Test creating a bank account
- `test_get_bank_accounts` - Test retrieving bank accounts
- `test_chatbot_interaction` - Test chatbot service
- `test_bill_payment_flow` - Test bill payment processing
- `test_complete_user_journey` - Full flow: create user → create account → get accounts → make payment → chat

**Expected Output Example**:
```
=== Testing Complete User Journey ===
Step 1: Creating user...
✓ User created (or already exists)
Step 2: Creating bank account...
✓ Bank account created
Step 3: Retrieving account info...
✓ Account info retrieved: 1 account(s)
Step 4: Making a payment...
✓ Payment processed
Step 5: Chatting with bot...
✓ Chatbot responded

✓ Complete user journey successful!
```

**Note**: Tests use the actual microservice APIs with proper data models:
- **User creation**: Requires `id`, `name`, `email`, `phone`, `address`, `income`, `preferred_language`, and preference objects
- **Account creation**: Requires `id`, `name`, `balance`, `routing_number`, `interest_rate`, `last_statement_date`, `account_type`
- **Bill payment**: Requires `billId`, `amount`, `currency`, `fromAccountId`, `toAccountId`
- **Chatbot**: Uses `prompt` query parameter

### test_scenario_service.py - Scenario Service API

Tests all scenario service API endpoints and configurations, including payment scenarios, chaos engineering, and load testing.

**Payment Scenario Tests**:
- `test_scenario_service_health` - Verify service is accessible
- `test_get_all_scenarios` - Retrieve all payment scenarios
- `test_reset_all_scenarios` - Reset all scenarios to disabled
- `test_enable_gateway_timeout` - Enable timeout with probability/delay
- `test_enable_card_decline` - Enable card decline scenario
- `test_enable_stolen_card` - Enable stolen card scenario
- `test_disable_scenario` - Disable a running scenario
- `test_multiple_scenarios_enabled` - Run multiple scenarios simultaneously
- `test_scenario_persistence` - Verify settings persist across requests

**Chaos Scenario Smoke Tests**:
- `test_chaos_scenarios_api` - Verify chaos API is available
- `test_chaos_enable_disable` - Basic enable/disable chaos scenarios

**Locust Load Testing Smoke Tests**:
- `test_locust_scenarios_api` - Verify locust API is available
- `test_locust_start_stop` - Basic start/stop load tests

**Expected Output Example**:
```
=== Testing Enable Gateway Timeout ===
Status: 200
Response: {'message': 'Gateway timeout scenario enabled'}
✓ Gateway timeout scenario enabled successfully

=== Testing Chaos Scenarios API ===
Available chaos scenarios: ['pod_delete', 'network_delay', 'cpu_stress']
✓ Chaos scenarios API available

=== Testing Locust Scenarios API ===
Locust status: {'running': False, 'users': 0}
✓ Locust scenarios API available
```

### Frontend Tests (Vitest) - Functional User Flow Tests

Tests critical user workflows in the frontend application using Vitest and React Testing Library.

**Technology Stack**:
- **Vitest** - Fast unit test framework
- **React Testing Library** - Component testing utilities
- **Happy DOM** - Lightweight DOM implementation

**Key Test Files**:
- `app/routes/login.test.tsx` - Login flow and authentication (4 tests)
- `app/components/dashboard/TransferCard.test.tsx` - Fund transfers and validation (5 tests)
- `app/routes/support.test.tsx` - Customer support chatbot integration (5 tests)
- `app/components/payments/PayBillCard.test.tsx` - Bill payment with Stripe integration (6 tests)

**Test Coverage**:
- **Login Flow**: Form submission, API integration, error handling, field interactions
- **Transfer Flow**: Amount validation, API requests, balance updates, error handling, transaction records
- **Support Chat Flow**: Bot responses, message sending, API integration, input validation
- **Bill Payment Flow**: Payment methods fetch, form validation, bank payments, Stripe card payments, error handling, form reset

**Example Commands**:
```bash
# Run all frontend tests
cd frontend_service && npm test

# Watch mode (re-run on changes)
npm run test:watch

# UI mode (interactive test runner)
npm run test:ui

# Coverage report
npm run test:coverage
```

**Expected Output Example**:
```
Test Files  4 passed (4)
     Tests  20 passed (20)
  Start at  12:04:56
  Duration  1.18s
```

### test_payment_scenarios.py - Payment Failures

Tests probability-based payment failure scenarios in detail.

**Key Tests**:
- `test_gateway_timeout_scenario` - Verify 504 timeout with delay
- `test_card_decline_scenario` - Verify 402 card decline
- `test_stolen_card_scenario` - Verify stolen card token usage
- `test_realistic_probability_distribution` - Test with realistic probabilities (20%)
- `test_scenario_reset` - Verify reset disables all scenarios

**Expected Output Example**:
```
=== Testing Realistic Probability Distribution ===
Sending 50 payment requests...

=== Results ===
Successful:       30 (60.0%)
Timeouts:          8 (16.0%)
Declines:         12 (24.0%)
Errors:            0 (0.0%)
Total failures:   20 (40.0%)

✓ Scenarios triggered correctly (failure rate: 40.0%)
```

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
- ✅ **Scenario API**: Enable/disable/reset payment scenarios, chaos scenarios (smoke tests), locust load testing (smoke tests)
- ✅ **Payment Scenarios**: Timeout, decline, stolen card with probabilities
- ✅ **Frontend Functional Tests**: Login flow, fund transfers, bill payment with Stripe, chatbot support, form validation, API integration, error handling (Vitest)

## Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Use environment variables for configuration
3. Include cleanup in fixtures or teardown
4. Add descriptive print statements for debugging
5. Update this README with new test descriptions
6. Ensure tests work both locally and remotely

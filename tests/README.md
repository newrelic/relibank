# Payment Scenario Tests

This directory contains automated tests for the Relibank payment failure scenarios. These tests verify that the probability-based payment scenarios (gateway timeout, card decline, and stolen card) work correctly.

## Prerequisites

1. **Services Running**: Ensure the Relibank stack is running locally:
   ```bash
   skaffold dev
   ```

2. **Python Dependencies**: Install required packages:
   ```bash
   pip install pytest requests
   ```

3. **Service Availability**: Verify services are accessible:
   - Bill Pay Service: http://localhost:5000
   - Scenario Service: http://localhost:8000

## Running the Tests

### Run All Tests Locally
```bash
pytest tests/test_payment_scenarios.py -v -s
```

### Run Tests Against Remote Environment
To test against a remote deployment, set the environment variables:

```bash
# Example: Testing against a remote server
export SCENARIO_SERVICE_URL="https://your-server.example.com/scenario-runner"
export BASE_URL="https://your-server.example.com"
pytest tests/test_payment_scenarios.py -v -s
```

Or as a one-liner:
```bash
SCENARIO_SERVICE_URL="https://your-server.example.com/scenario-runner" BASE_URL="https://your-server.example.com" pytest tests/test_payment_scenarios.py -v -s
```

### Run Individual Tests
```bash
# Test gateway timeout scenario
pytest tests/test_payment_scenarios.py::test_gateway_timeout_scenario -v -s

# Test card decline scenario
pytest tests/test_payment_scenarios.py::test_card_decline_scenario -v -s

# Test stolen card scenario
pytest tests/test_payment_scenarios.py::test_stolen_card_scenario -v -s

# Test realistic probability distribution
pytest tests/test_payment_scenarios.py::test_realistic_probability_distribution -v -s

# Test scenario reset functionality
pytest tests/test_payment_scenarios.py::test_scenario_reset -v -s
```

## Test Descriptions

### 1. test_gateway_timeout_scenario
**Purpose**: Verifies gateway timeout scenario triggers correctly

**What it does**:
- Enables gateway timeout with 100% probability and 2s delay
- Sends a single card payment
- Verifies 504 timeout response
- Confirms at least 2 second delay occurred

**Expected output**:
```
=== Testing Gateway Timeout Scenario ===
Enabled: Gateway timeout scenario enabled (100.0% of requests)
Response status: 504
Response body: {'detail': 'Payment gateway timeout - please try again later'}
Elapsed time: 2.XX s
✓ Gateway timeout scenario working correctly
PASSED
```

### 2. test_card_decline_scenario
**Purpose**: Verifies card decline scenario triggers correctly

**What it does**:
- Enables card decline with 100% probability
- Sends 5 card payments with different amounts
- Counts how many get declined (402 status)
- Verifies all 5 are declined

**Expected output**:
```
=== Testing Card Decline Scenario ===
Enabled: Card decline scenario enabled (100.0% of requests)
Payment 1: DECLINED - Payment declined by card issuer. Please try a different payment method or contact your bank.
Payment 2: DECLINED - Payment declined by card issuer. Please try a different payment method or contact your bank.
Payment 3: DECLINED - Payment declined by card issuer. Please try a different payment method or contact your bank.
Payment 4: DECLINED - Payment declined by card issuer. Please try a different payment method or contact your bank.
Payment 5: DECLINED - Payment declined by card issuer. Please try a different payment method or contact your bank.

Declined: 5/5 payments
✓ Card decline scenario working correctly
PASSED
```

### 3. test_stolen_card_scenario
**Purpose**: Verifies stolen card scenario uses Stripe test token

**What it does**:
- Enables stolen card with 100% probability
- Sends 5 card payments
- Verifies Stripe declines them using the stolen card test token
- Confirms all 5 are declined with 402 status

**Expected output**:
```
=== Testing Stolen Card Scenario ===
Enabled: Stolen card scenario enabled (100.0% of requests)
Payment 1: DECLINED - Card declined: Your card was declined.
Payment 2: DECLINED - Card declined: Your card was declined.
Payment 3: DECLINED - Card declined: Your card was declined.
Payment 4: DECLINED - Card declined: Your card was declined.
Payment 5: DECLINED - Card declined: Your card was declined.

Declined (stolen card): 5/5 payments
✓ Stolen card scenario working correctly
PASSED
```

### 4. test_realistic_probability_distribution
**Purpose**: Verifies scenarios work with realistic probabilities

**What it does**:
- Enables all 3 scenarios with 20% probability each
- Sends 50 payment requests
- Tracks success/timeout/decline/error counts
- Verifies distribution matches expected probabilities

**Expected output**:
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
PASSED
```

**Note**: Due to randomness, exact percentages will vary but should be roughly:
- 40-60% failures total (combination of timeouts and declines)
- Some timeouts (~10-30%)
- Some declines (~10-30%)
- Some successes (~40-60%)

### 5. test_scenario_reset
**Purpose**: Verifies reset functionality disables all scenarios

**What it does**:
- Enables all scenarios with 100% probability
- Calls reset endpoint
- Sends a payment
- Verifies payment succeeds (200 status)

**Expected output**:
```
=== Testing Scenario Reset ===
Reset all scenarios
Response status: 200
✓ Scenario reset working correctly
PASSED
```

## Understanding Test Results

### Success Indicators
- ✓ All tests pass
- Status codes match expectations (504 for timeout, 402 for declines, 200 for success)
- Probabilities result in expected failure rates
- Delays are observed for timeout scenarios

### Troubleshooting

**Services not accessible**:
```
requests.exceptions.ConnectionError: Failed to establish a new connection
```
→ Ensure `skaffold dev` is running and services are healthy

**All payments succeed when they should fail**:
```
AssertionError: Expected 5 declines with 100% probability, got 0
```
→ Check scenario service logs to verify scenarios are being enabled
→ Verify bill pay service can reach scenario service

**Timeouts not occurring**:
```
AssertionError: Expected at least 2s delay, got 0.05s
```
→ Check bill pay service is fetching scenarios from scenario service
→ Verify gateway timeout scenario logic in bill_pay_service.py

**Stripe errors**:
```
Error: Stripe payment processing is not configured
```
→ Ensure STRIPE_SECRET_KEY is set in skaffold.env
→ Verify Stripe keys are passed to bill pay service container

## Cleanup

Tests automatically reset scenarios before and after each test run. If tests are interrupted, you can manually reset:

```bash
curl -X POST http://localhost:8000/scenario-runner/api/payment-scenarios/reset
```

## Integration with CI/CD

These tests can be added to GitHub Actions or other CI pipelines:

```yaml
- name: Run payment scenario tests
  env:
    SCENARIO_SERVICE_URL: ${{ vars.SCENARIO_SERVICE_URL }}
    BASE_URL: ${{ vars.BASE_URL }}
  run: |
    pip install pytest requests
    pytest tests/test_payment_scenarios.py -v
```

The tests automatically use environment variables for configuration:
- `SCENARIO_SERVICE_URL`: URL to the scenario runner service (default: `http://localhost:8000/scenario-runner`)
- `BASE_URL`: Base URL to the bill pay service (default: `http://localhost:5000`)

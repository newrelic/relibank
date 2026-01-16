# Relibank Tests - Quick Start Guide

Get started with Relibank testing in under 5 minutes.

## 🚀 Quick Setup

### 1. Install Dependencies

Run the setup script to create a virtual environment and install all dependencies:

```bash
cd tests
./setup_test_env.sh
```

This will:
- Create a Python virtual environment (`.venv-relibank-tests`)
- Install pytest and requests
- Verify your Python installation

### 2. Activate the Environment

```bash
source .venv-relibank-tests/bin/activate
```

### 3. Run Tests

**Test everything:**
```bash
pytest tests/ -v
```

**Test specific components:**
```bash
# End-to-end service tests
pytest tests/test_end_to_end.py -v

# Scenario service API tests
pytest tests/test_scenario_service.py -v

# Payment scenario tests
pytest tests/test_payment_scenarios.py -v
```

## 🌐 Testing Against Different Environments

### Local Testing (Default)

When services are running locally (via `skaffold dev`):

```bash
pytest tests/ -v
```

Services expected at:
- Frontend: http://localhost:3000
- Accounts: http://localhost:5002
- Bill Pay: http://localhost:5000
- Chatbot: http://localhost:5003
- Scenario Runner: http://localhost:8000/scenario-runner

### Remote Testing

Test against a deployed environment:

```bash
# Set the remote URL environment variable
export RELIBANK_URL="http://your-server.example.com"

# Option 1: Use the helper script (recommended)
./run_tests.sh -e remote -t e2e

# Option 2: Manually set all environment variables and run pytest
export BASE_URL="$RELIBANK_URL"
export ACCOUNTS_SERVICE="$RELIBANK_URL/accounts"
export BILL_PAY_SERVICE="$RELIBANK_URL/billpay"
export CHATBOT_SERVICE="$RELIBANK_URL/chatbot"
export SCENARIO_SERVICE_URL="$RELIBANK_URL/scenario-runner"

pytest tests/test_end_to_end.py -v
pytest tests/test_scenario_service.py -v
```


## 📊 Understanding Test Results

### Successful Test
```
tests/test_end_to_end.py::test_frontend_loads
=== Testing Frontend ===
Status: 200
✓ Frontend loads successfully
PASSED
```

### Skipped Test (Rare)
```
tests/test_scenario_service.py::test_chaos_scenarios_api SKIPPED
```

Tests may be skipped when:
- Optional features not implemented
- Services temporarily unavailable

This is **normal** - tests gracefully skip instead of failing.

### Failed Test (Needs Investigation)
```
tests/test_end_to_end.py::test_accounts_service_health FAILED
AssertionError: Accounts service health check failed: 500
```

Failed tests indicate actual issues that need investigation.

## 🧪 Common Test Scenarios

### Test Frontend Only
```bash
pytest tests/test_end_to_end.py::test_frontend_loads -v
```

### Test All Microservices
```bash
pytest tests/test_end_to_end.py -k "health" -v
```

### Test Payment Scenarios
```bash
pytest tests/test_scenario_service.py -k "payment" -v
```

### Test Complete User Journey
```bash
pytest tests/test_end_to_end.py::test_complete_user_journey -v -s
```

## 🐛 Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'pytest'`

**Solution**: Activate the virtual environment:
```bash
source .venv-relibank-tests/bin/activate
```

### Problem: Tests timeout or fail to connect

**Solution**:
1. Verify services are running: `kubectl get pods -n relibank`
2. Check service URLs are correct
3. Check firewall/network settings

### Problem: `Connection refused` errors

**Solution**:
- **Local**: Ensure `skaffold dev` is running
- **Remote**: Verify the remote URL is correct and services are deployed

## 📁 Test Files

| File | Purpose | What It Tests |
|------|---------|---------------|
| `test_end_to_end.py` | Microservice integration | Frontend, accounts, bill pay, chatbot, user flows |
| `test_scenario_service.py` | Scenario API | Payment failures, chaos, load testing |
| `test_payment_scenarios.py` | Payment behaviors | Timeout, decline, stolen card scenarios |

## 🔄 Deactivating the Environment

When you're done testing:

```bash
deactivate
```

## 📚 Full Documentation

For comprehensive documentation including:
- All environment variables
- CI/CD integration
- Contributing guidelines
- Detailed test descriptions

See [README.md](README.md) in the tests directory.

## ⚡ One-Line Test Commands

**Quick smoke test (local):**
```bash
source .venv-relibank-tests/bin/activate && pytest tests/test_end_to_end.py::test_frontend_loads tests/test_scenario_service.py::test_scenario_service_health -v
```

**Quick smoke test (remote):**
```bash
export RELIBANK_URL="http://your-server.example.com"
source .venv-relibank-tests/bin/activate && ./run_tests.sh -e remote -t smoke
```

**Full test suite (local):**
```bash
source .venv-relibank-tests/bin/activate && pytest tests/ -v --tb=short
```

## 💡 Tips

1. **Use `-s` flag** to see print statements: `pytest tests/test_end_to_end.py -v -s`
2. **Run specific tests** with `-k`: `pytest -k "payment" -v`
3. **Stop on first failure** with `-x`: `pytest tests/ -v -x`
4. **See full output** with `-vv`: `pytest tests/ -vv`
5. **Parallel execution** (if installed pytest-xdist): `pytest tests/ -n auto`

## 🎯 Next Steps

- Explore [README.md](README.md) for comprehensive documentation
- Check individual test files for detailed test implementations
- Set up CI/CD integration (see README.md)
- Customize environment variables for your deployment

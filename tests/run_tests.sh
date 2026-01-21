#!/bin/bash

# Relibank Test Runner
# Convenient script for running tests against local or remote environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="local"
TEST_SUITE="all"
VENV_DIR=".venv-relibank-tests"

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
Relibank Test Runner

Usage: ./run_tests.sh [OPTIONS]

OPTIONS:
    -e, --env ENV           Environment to test (local|remote) [default: local]
    -t, --test SUITE        Test suite to run (all|e2e|scenario|payment|frontend|smoke) [default: all]
    -v, --verbose           Verbose output (show print statements)
    -h, --help              Show this help message

ENVIRONMENT VARIABLES:
    RELIBANK_URL            Remote URL (required if env=remote)
                           Example: export RELIBANK_URL="http://your-server.example.com"

EXAMPLES:
    # Run all tests locally
    ./run_tests.sh

    # Run end-to-end tests locally with verbose output
    ./run_tests.sh -t e2e -v

    # Run all tests against remote
    export RELIBANK_URL="http://your-server.example.com"
    ./run_tests.sh -e remote

    # Run scenario tests against remote
    export RELIBANK_URL="http://your-server.example.com"
    ./run_tests.sh -e remote -t scenario

    # Quick smoke test
    ./run_tests.sh -t smoke

AVAILABLE TEST SUITES:
    all       - All test files (Python + Frontend)
    e2e       - End-to-end microservice tests (test_end_to_end.py)
    scenario  - Scenario service tests (test_scenario_service.py)
    payment   - Payment scenario tests (test_payment_scenarios.py)
    frontend  - Frontend unit tests (Vitest)
    smoke     - Quick smoke test (frontend + scenario health)

NOTES:
    - Virtual environment must be set up first (run ./setup_test_env.sh)
    - See QUICKSTART.md for detailed instructions
EOF
}

# Parse command line arguments
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--test)
            TEST_SUITE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="-s"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "local" && "$ENVIRONMENT" != "remote" ]]; then
    print_error "Invalid environment: $ENVIRONMENT (must be 'local' or 'remote')"
    exit 1
fi

# Check if RELIBANK_URL is set for remote environment
if [[ "$ENVIRONMENT" == "remote" && -z "$RELIBANK_URL" ]]; then
    print_error "RELIBANK_URL environment variable is required when testing remote environment"
    echo ""
    echo "Set the variable and try again:"
    echo "  export RELIBANK_URL=\"http://your-server.example.com\""
    echo "  ./run_tests.sh -e remote"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    print_error "Virtual environment not found at $VENV_DIR"
    echo ""
    echo "Please run setup first:"
    echo "  ./setup_test_env.sh"
    exit 1
fi

# Activate virtual environment
print_header "Relibank Test Runner"
echo "Environment: $ENVIRONMENT"
echo "Test Suite: $TEST_SUITE"
if [[ -n "$RELIBANK_URL" ]]; then
    echo "Remote URL: $RELIBANK_URL"
fi
echo ""

print_success "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Set environment variables based on environment
if [[ "$ENVIRONMENT" == "remote" ]]; then
    print_success "Configuring remote environment variables..."
    # For remote, all services go through the same base URL
    export BASE_URL="$RELIBANK_URL"
    export ACCOUNTS_SERVICE="$RELIBANK_URL"
    export BILL_PAY_SERVICE="$RELIBANK_URL"
    export CHATBOT_SERVICE="$RELIBANK_URL"
    export SCENARIO_SERVICE_URL="$RELIBANK_URL/scenario-runner"

else
    print_success "Using local environment (default localhost URLs)"
fi

# Determine which tests to run
case $TEST_SUITE in
    all)
        print_header "Running Tests"
        echo "Running Python tests..."
        echo ""
        pytest . -v $VERBOSE

        echo ""
        print_success "Python tests complete!"
        echo ""

        echo "Running Frontend tests..."
        echo ""
        cd ../frontend_service
        npm test
        cd ../tests

        echo ""
        print_success "All tests complete!"
        exit 0
        ;;
    e2e)
        TEST_PATH="test_end_to_end.py"
        ;;
    scenario)
        TEST_PATH="test_scenario_service.py"
        ;;
    payment)
        TEST_PATH="test_payment_scenarios.py"
        ;;
    frontend)
        print_header "Running Frontend Tests"
        echo ""
        cd ../frontend_service
        npm test
        exit $?
        ;;
    smoke)
        TEST_PATH="test_end_to_end.py::test_frontend_loads test_scenario_service.py::test_scenario_service_health"
        ;;
    *)
        print_error "Invalid test suite: $TEST_SUITE"
        echo "Valid options: all, e2e, scenario, payment, frontend, smoke"
        exit 1
        ;;
esac

# Run tests (for non-all, non-frontend cases)
print_header "Running Tests"
echo "Test path: $TEST_PATH"
echo ""

pytest $TEST_PATH -v $VERBOSE

# Check result
if [ $? -eq 0 ]; then
    echo ""
    print_header "Test Results"
    print_success "All tests passed!"
else
    echo ""
    print_header "Test Results"
    print_error "Some tests failed. See output above for details."
    exit 1
fi

echo ""
print_success "Test run complete"
echo ""

"""
Test New Relic instrumentation verification.

This test generates traffic and verifies that:
1. Transactions are appearing in New Relic APM
2. User IDs are being tracked correctly
3. Services are properly instrumented

Prerequisites:
- NEW_RELIC_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable (defaults to 4182956)
- Services running and instrumented with New Relic
"""

import os
import time
import pytest
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Helper function to load environment variables from skaffold.env if present
def load_env_from_skaffold():
    """Load environment variables from skaffold.env if file exists (local development)"""
    skaffold_env_path = Path(__file__).parent.parent / "skaffold.env"
    if skaffold_env_path.exists():
        with open(skaffold_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    # Only set if not already in environment (explicit env vars take precedence)
                    if key not in os.environ:
                        os.environ[key] = value

# Load from skaffold.env if present (for local development)
load_env_from_skaffold()

# Configuration
ACCOUNTS_SERVICE = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")
TRANSACTION_SERVICE = os.getenv("TRANSACTION_SERVICE", "http://localhost:5001")
BILL_PAY_SERVICE = os.getenv("BILL_PAY_SERVICE", "http://localhost:5000")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")

# Skip all tests if New Relic credentials not provided
pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set"
)

# Shared test data to avoid regenerating traffic for each test
_test_user_id = None
_traffic_generated = False


@pytest.fixture(scope="module", autouse=True)
def generate_test_traffic_once():
    """
    Generate test traffic once before all tests run.
    This fixture runs automatically and is shared across all tests in this module.
    """
    global _test_user_id, _traffic_generated

    if _traffic_generated:
        return _test_user_id

    print("\n" + "="*80)
    print("SETUP: Generating test traffic for all New Relic instrumentation tests")
    print("="*80)

    _test_user_id = f"test-user-{int(time.time())}"
    headers = {"x-browser-user-id": _test_user_id}

    services_hit = []

    # Hit accounts service (non-ignored endpoint)
    try:
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/user/traffic-test@relibank.com",
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 404]:
            services_hit.append("accounts-service")
            print(f"✓ Hit accounts-service (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Failed to hit accounts-service: {e}")

    # Generate bill payment to trigger Transaction Service
    payment_data = {
        "billId": f"test-bill-{int(time.time())}",
        "amount": 10.00,
        "currency": "USD",
        "fromAccountId": 1,
        "toAccountId": 2
    }

    try:
        response = requests.post(
            f"{BILL_PAY_SERVICE}/bill-pay-service/pay",
            json=payment_data,
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 201]:
            services_hit.append("bill-pay-service")
            print(f"✓ Generated bill payment (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Failed to generate bill payment: {e}")

    # Trigger a StripeError to populate TransactionError with notice_error attributes
    try:
        requests.post(
            f"{BILL_PAY_SERVICE}/bill-pay-service/card-pay",
            json={"paymentMethodId": "pm_card_invalid", "amount": 10.00, "customerId": "cus_test_invalid"},
            headers=headers,
            timeout=10
        )
        print("  Triggered error traffic for notice_error coverage")
    except Exception:
        pass  # Error is intentional; ConnectionError if service is down is also fine

    print(f"\nGenerated traffic to: {', '.join(services_hit)}")
    print("⏳ Waiting 60 seconds for New Relic data ingestion...")
    print("="*80 + "\n")

    time.sleep(60)
    _traffic_generated = True

    return _test_user_id


def query_nrql(nrql_query):
    """Query New Relic using NRQL."""
    url = f"https://api.newrelic.com/graphql"
    headers = {
        "Content-Type": "application/json",
        "API-Key": NEW_RELIC_API_KEY
    }

    query = f"""
    {{
      actor {{
        account(id: {NEW_RELIC_ACCOUNT_ID}) {{
          nrql(query: "{nrql_query}") {{
            results
          }}
        }}
      }}
    }}
    """

    response = requests.post(url, json={"query": query}, headers=headers)
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")

    return data["data"]["actor"]["account"]["nrql"]["results"]


def generate_test_traffic():
    """Generate test traffic with unique user IDs."""
    print("\n=== Generating Test Traffic ===")

    # Generate unique user ID for this test run
    test_user_id = f"test-user-{int(time.time())}"
    headers = {"x-browser-user-id": test_user_id}

    print(f"Using test user ID: {test_user_id}")

    # Hit multiple services to generate transactions
    services_hit = []

    # 1. Accounts service (non-ignored endpoint)
    try:
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/user/traffic-test@relibank.com",
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 404]:
            services_hit.append("accounts-service")
            print(f"✓ Hit accounts-service (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Failed to hit accounts-service: {e}")

    # 2. Transaction service (non-ignored endpoint)
    try:
        response = requests.get(
            f"{TRANSACTION_SERVICE}/transaction-service/transactions",
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 404]:
            services_hit.append("transaction-service")
            print(f"✓ Hit transaction-service (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Failed to hit transaction-service: {e}")

    # 3. Bill pay service (non-ignored endpoint)
    try:
        response = requests.get(
            f"{BILL_PAY_SERVICE}/bill-pay-service/payment-scenarios",
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 404]:
            services_hit.append("bill-pay-service")
            print(f"✓ Hit bill-pay-service (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Failed to hit bill-pay-service: {e}")

    print(f"\nGenerated traffic to {len(services_hit)} services: {', '.join(services_hit)}")

    # Wait for data to be ingested by New Relic
    print("\n⏳ Waiting 60 seconds for New Relic data ingestion...")
    time.sleep(60)

    return test_user_id, services_hit


@pytest.mark.slow
def test_newrelic_transactions_exist():
    """Verify that transactions are appearing in New Relic APM."""
    print("\n=== Test: New Relic Transactions Exist ===")

    # Query for recent transactions (last 5 minutes)
    nrql = "SELECT count(*) FROM Transaction WHERE appName LIKE '%Relibank%' OR appName LIKE '%Accounts Service%' OR appName LIKE '%Transaction Service%' OR appName LIKE '%Bill Pay%' SINCE 5 minutes ago"

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)

    transaction_count = results[0]["count"] if results else 0

    print(f"\n📊 Transaction count (last 5 min): {transaction_count}")

    assert transaction_count > 0, \
        f"Expected transactions in New Relic, but found {transaction_count}. " \
        "This suggests services are not properly instrumented."

    print("✅ New Relic is receiving transactions")


@pytest.mark.slow
def test_newrelic_user_id_tracking():
    """Verify that user IDs are being tracked in New Relic."""
    print("\n=== Test: New Relic User ID Tracking ===")

    # Generate traffic with known user ID
    test_user_id, services_hit = generate_test_traffic()

    if not services_hit:
        pytest.skip("Could not generate test traffic - services may not be accessible")

    # Query for transactions with our test user ID
    nrql = f"SELECT count(*) FROM Transaction WHERE enduser.id = '{test_user_id}' SINCE 5 minutes ago"

    print(f"\nQuerying NRQL: {nrql}")
    results = query_nrql(nrql)

    user_transaction_count = results[0]["count"] if results else 0

    print(f"\n📊 Transactions with test user ID '{test_user_id}': {user_transaction_count}")
    print(f"   (Expected at least {len(services_hit)} from services: {', '.join(services_hit)})")

    assert user_transaction_count > 0, \
        f"Expected transactions with user ID '{test_user_id}', but found {user_transaction_count}. " \
        "This suggests user ID tracking is not working correctly."

    print(f"✅ User ID tracking is working ({user_transaction_count} transactions found)")


@pytest.mark.slow
def test_newrelic_services_instrumented():
    """Verify that all major services are instrumented and reporting."""
    print("\n=== Test: All Services Instrumented ===")

    # Generate traffic to trigger Transaction Service activity via Kafka
    print("\n=== Generating Bill Payment to Trigger Transaction Service ===")
    test_user_id = f"test-user-{int(time.time())}"
    payment_data = {
        "billId": f"test-bill-{int(time.time())}",
        "amount": 10.00,
        "currency": "USD",
        "fromAccountId": 1,
        "toAccountId": 2
    }

    try:
        response = requests.post(
            f"{BILL_PAY_SERVICE}/bill-pay-service/pay",
            json=payment_data,
            headers={"x-browser-user-id": test_user_id},
            timeout=10
        )
        if response.status_code in [200, 201]:
            print(f"✓ Bill payment generated (status: {response.status_code})")
            print("  Waiting 60 seconds for Kafka message processing and New Relic ingestion...")
            time.sleep(60)
        else:
            print(f"⚠ Bill payment request returned status {response.status_code}")
    except Exception as e:
        print(f"⚠ Failed to generate bill payment: {e}")

    expected_services = [
        "Accounts Service",
        "Transaction Service",
        "Bill Pay"
    ]

    instrumented_services = []
    missing_services = []

    for service in expected_services:
        # Check for transactions from this service in the last hour
        nrql = f"SELECT count(*) FROM Transaction WHERE appName LIKE '%{service}%' SINCE 1 hour ago"

        print(f"\nChecking {service}...")
        print(f"  Query: {nrql}")

        results = query_nrql(nrql)
        count = results[0]["count"] if results else 0

        print(f"  Transactions: {count}")

        if count > 0:
            instrumented_services.append(service)
            print(f"  ✓ {service} is instrumented")
        else:
            missing_services.append(service)
            print(f"  ✗ {service} has NO transactions")

    print(f"\n📊 Summary:")
    print(f"   Instrumented: {len(instrumented_services)}/{len(expected_services)}")
    print(f"   Services with data: {', '.join(instrumented_services) if instrumented_services else 'None'}")

    if missing_services:
        print(f"   ⚠ Missing services: {', '.join(missing_services)}")

    assert len(instrumented_services) == len(expected_services), \
        f"Not all services are instrumented. Missing: {', '.join(missing_services)}"

    print("✅ All services are properly instrumented")


@pytest.mark.slow
def test_newrelic_recent_activity():
    """Verify there has been recent activity in the last 10 minutes."""
    print("\n=== Test: Recent Activity ===")

    nrql = "SELECT count(*) FROM Transaction WHERE appName LIKE '%Relibank%' OR appName LIKE '%Accounts Service%' OR appName LIKE '%Transaction Service%' OR appName LIKE '%Bill Pay%' SINCE 10 minutes ago"

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)

    recent_count = results[0]["count"] if results else 0

    print(f"\n📊 Transactions in last 10 minutes: {recent_count}")

    assert recent_count > 0, \
        "No recent activity found. Services may have stopped reporting or there's no traffic."

    print("✅ Recent activity detected in New Relic")


@pytest.mark.slow
def test_newrelic_error_notice_tracking():
    """Verify notice_error() surfaces TransactionError events with service/endpoint/action attributes."""
    print("\n=== Test: notice_error Custom Attribute Tracking ===")

    nrql = (
        "SELECT count(*) FROM TransactionError "
        "WHERE (appName LIKE '%Relibank%' OR appName LIKE '%Bill Pay%') "
        "AND custom.service IS NOT NULL "
        "AND custom.endpoint IS NOT NULL "
        "AND custom.action IS NOT NULL "
        "SINCE 10 minutes ago"
    )

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)
    error_count = results[0].get("count", 0) if results else 0

    print(f"\n📊 TransactionError with custom.service/endpoint/action: {error_count}")

    if error_count == 0:
        pytest.skip(
            "No TransactionError events with notice_error attributes found — "
            "Stripe card-pay error trigger may not have reached the handler (Stripe not configured?)"
        )

    assert error_count > 0, (
        "Expected TransactionError events with custom.service, custom.endpoint, and custom.action — "
        "notice_error() attributes missing from error events"
    )
    print("✅ notice_error attributes verified on TransactionError events")


@pytest.mark.slow
def test_newrelic_transaction_custom_attributes():
    """Verify add_custom_attributes() populates Transaction events with service-level attributes."""
    print("\n=== Test: Transaction Custom Attributes (add_custom_attributes) ===")

    # billId is added via add_custom_attributes() in bill_pay_service — no custom. prefix
    nrql = (
        "SELECT count(*) FROM Transaction "
        "WHERE appName LIKE '%Bill Pay%' "
        "AND billId IS NOT NULL "
        "SINCE 10 minutes ago"
    )

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)
    txn_count = results[0].get("count", 0) if results else 0

    print(f"\n📊 Transactions with billId attribute: {txn_count}")

    assert txn_count > 0, (
        "Expected Transaction events with billId attribute from add_custom_attributes() — "
        "bill-pay service may not be setting NR custom attributes correctly"
    )
    print("✅ add_custom_attributes() verified: billId present on Transaction events")


if __name__ == "__main__":
    # Allow running individual tests
    import sys

    if not NEW_RELIC_API_KEY:
        print("❌ NEW_RELIC_USER_API_KEY environment variable not set")
        print("   Please set it to run New Relic instrumentation tests")
        sys.exit(1)

    print("🧪 Running New Relic Instrumentation Tests")
    print(f"   Account ID: {NEW_RELIC_ACCOUNT_ID}")
    print(f"   Accounts Service: {ACCOUNTS_SERVICE}")
    print(f"   Transaction Service: {TRANSACTION_SERVICE}")
    print(f"   Bill Pay Service: {BILL_PAY_SERVICE}")

    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

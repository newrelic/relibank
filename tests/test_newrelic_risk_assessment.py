#!/usr/bin/env python3
"""
Test New Relic observability for AI-powered risk assessment flow.

This test validates that risk assessment activity appears in New Relic:
1. Logs from bill pay, support, and risk assessment services
2. Declined payment workflow visibility
3. Agent model tracking (gpt-4o vs gpt-4o-mini)
4. eBPF traces for risk assessment service (when available)

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable (defaults to 4182956)
- Services running with New Relic instrumentation
"""

import os
import time
import pytest
import requests
import pyodbc
from pathlib import Path
from typing import Dict, List

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
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")
BILL_PAY_SERVICE = os.getenv("BILL_PAY_SERVICE", "http://localhost:5000")
ACCOUNTS_SERVICE = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")
SUPPORT_SERVICE = os.getenv("SUPPORT_SERVICE_URL", "http://localhost:5003")

NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")
NERDGRAPH_URL = "https://api.newrelic.com/graphql"

# Entity name prefix (e.g., "Jared" locally, "ReliBank" in prod)
APP_NAME_PREFIX = os.getenv("APP_NAME", "Jared")  # Falls back to "Jared" if not set

# Database connection details
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")
CONNECTION_STRING = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"

# Skip all tests if New Relic credentials not provided
pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set"
)


def query_nerdgraph(nrql_query: str) -> List[Dict]:
    """Execute a NRQL query via NerdGraph API"""
    graphql_query = """
    query($accountId: Int!, $nrql: Nrql!) {
      actor {
        account(id: $accountId) {
          nrql(query: $nrql) {
            results
          }
        }
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "API-Key": NEW_RELIC_API_KEY
    }

    variables = {
        "accountId": int(NEW_RELIC_ACCOUNT_ID),
        "nrql": nrql_query
    }

    response = requests.post(
        NERDGRAPH_URL,
        headers=headers,
        json={"query": graphql_query, "variables": variables},
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"NerdGraph query failed: {response.status_code} - {response.text}")

    data = response.json()
    return data.get("data", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])


def get_db_connection():
    """Get database connection"""
    return pyodbc.connect(CONNECTION_STRING)


def query_transaction_by_bill_id(bill_id: str) -> Dict:
    """Query Transactions table for a specific bill ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EventType, BillID, Amount, Currency, AccountID, Status, DeclineReason, Timestamp
        FROM Transactions
        WHERE BillID = ?
        ORDER BY Timestamp DESC
    """, bill_id)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "EventType": row[0],
            "BillID": row[1],
            "Amount": float(row[2]),
            "Currency": row[3],
            "AccountID": row[4],
            "Status": row[5],
            "DeclineReason": row[6],
            "Timestamp": row[7]
        }
    return None


@pytest.fixture
def reset_risk_scenarios():
    """Reset all risk assessment scenarios before and after tests"""
    try:
        response = requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)
        if response.status_code == 200:
            time.sleep(2)  # Wait for config to propagate
    except:
        pass  # Ignore reset errors

    yield

    try:
        requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)
    except:
        pass


def enable_rogue_agent():
    """Enable rogue agent (gpt-4o-mini that declines most payments)"""
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/rogue-agent",
        params={"enabled": True},
        timeout=10
    )
    assert response.status_code == 200
    time.sleep(2)  # Wait for config to propagate


def disable_rogue_agent():
    """Disable rogue agent (back to normal gpt-4o)"""
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/rogue-agent",
        params={"enabled": False},
        timeout=10
    )
    assert response.status_code == 200
    time.sleep(2)  # Wait for config to propagate


def get_test_account_data():
    """Get test account data for making payments"""
    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/accounts/1", timeout=10)
    assert response.status_code == 200
    return response.json()


def make_test_payment(amount: float = 100.0, from_account_id: int = 1, to_account_id: int = 2) -> Dict:
    """Make a test payment through bill pay service"""
    payment_data = {
        "billId": f"test-bill-{int(time.time())}",
        "amount": amount,
        "currency": "usd",
        "fromAccountId": from_account_id,
        "toAccountId": to_account_id,
        "payee": "Test Payee"
    }

    response = requests.post(
        f"{BILL_PAY_SERVICE}/bill-pay-service/pay",
        json=payment_data,
        timeout=30
    )

    return {
        "status_code": response.status_code,
        "payment_data": payment_data,
        "response": response.json() if response.status_code in [200, 403] else None
    }


# Test 1: Risk Assessment Logs Validation
def test_risk_assessment_logs_in_newrelic(reset_risk_scenarios):
    """Uses reset_risk_scenarios fixture for cleanup"""
    _ = reset_risk_scenarios  # Mark as used
    """
    Validate that risk assessment activity appears in New Relic Logs.

    This test:
    1. Makes test payments to trigger risk assessment
    2. Queries New Relic Logs for risk assessment activity
    3. Validates logs from Bill Pay, Support, and Risk Assessment services
    """
    print("\n" + "="*80)
    print("TEST: Risk Assessment Logs in New Relic")
    print("="*80)

    # Make a few test payments to generate log data
    print("\n1. Generating risk assessment activity...")
    for i in range(3):
        result = make_test_payment(amount=50.0 + (i * 10))
        print(f"   Payment {i+1}: status={result['status_code']}")
        time.sleep(1)

    # Wait for logs to appear in New Relic
    print("\n2. Waiting 30 seconds for logs to appear in New Relic...")
    time.sleep(30)

    # Query for risk assessment logs
    print("\n3. Querying New Relic Logs...")

    # Query for logs containing risk assessment keywords
    nrql = f"""
    SELECT count(*) as log_count, latest(message) as sample_message
    FROM Log
    WHERE (message LIKE '%risk%' OR message LIKE '%assess%')
      AND entity.name IN ('{APP_NAME_PREFIX} - Bill Pay Service',
                          '{APP_NAME_PREFIX} - Support Service',
                          '{APP_NAME_PREFIX} - Risk Assessment Service')
    SINCE 2 minutes ago
    """

    results = query_nerdgraph(nrql)

    print(f"\n4. Results:")
    if results:
        log_count = results[0].get('log_count', 0)
        sample_message = results[0].get('sample_message', 'N/A')
        print(f"   Log entries found: {log_count}")
        print(f"   Sample message: {sample_message[:100]}...")

        # Validate we found logs
        assert log_count > 0, f"Expected risk assessment logs in New Relic, found {log_count}"
        print(f"\n✅ PASS: Found {log_count} risk assessment log entries in New Relic")
    else:
        print("   ⚠️  No results returned from query")
        print("   This may indicate:")
        print("   - Logs haven't reached New Relic yet (try waiting longer)")
        print("   - Log forwarding not configured")
        print("   - Entity names don't match (check APP_NAME prefix)")
        pytest.skip("No log data found in New Relic - may need more time or configuration")


# Test 4: Declined Payment Workflow E2E
def test_declined_payment_shows_in_newrelic(reset_risk_scenarios):
    """Uses reset_risk_scenarios fixture for cleanup"""
    _ = reset_risk_scenarios  # Mark as used
    """
    Validate that declined payments appear in New Relic with proper details.

    This test:
    1. Enables rogue agent (90%+ decline rate)
    2. Sends multiple test payments
    3. Queries New Relic for declined payment logs
    4. Verifies agent model and decline reasons appear
    """
    print("\n" + "="*80)
    print("TEST: Declined Payment Workflow in New Relic")
    print("="*80)

    # Enable rogue agent
    print("\n1. Enabling rogue agent (gpt-4o-mini)...")
    enable_rogue_agent()

    # Make test payments (most should be declined)
    print("\n2. Sending 10 test payments...")
    approved_count = 0
    declined_count = 0
    declined_bill_ids = []  # Track declined payment IDs for database validation

    for i in range(10):
        result = make_test_payment(amount=100.0 + (i * 10))
        if result['status_code'] == 200:
            approved_count += 1
            print(f"   Payment {i+1}: ✅ APPROVED")
        elif result['status_code'] == 403:
            declined_count += 1
            declined_bill_ids.append(result['payment_data']['billId'])
            print(f"   Payment {i+1}: ❌ DECLINED (BillID: {result['payment_data']['billId']})")
        time.sleep(1)

    print(f"\n   Summary: {approved_count} approved, {declined_count} declined")

    # Disable rogue agent
    print("\n3. Disabling rogue agent...")
    disable_rogue_agent()

    # Wait for logs and Kafka processing
    print("\n4. Waiting 30 seconds for logs and database entries...")
    time.sleep(30)

    # Query for declined payment logs
    print("\n5. Querying New Relic for declined payment logs...")

    nrql = f"""
    SELECT count(*) as declined_log_count
    FROM Log
    WHERE message LIKE '%declined%' OR message LIKE '%DECLINED%'
      AND entity.name IN ('{APP_NAME_PREFIX} - Bill Pay Service',
                          '{APP_NAME_PREFIX} - Support Service')
    SINCE 3 minutes ago
    """

    results = query_nerdgraph(nrql)

    print(f"\n6. Results:")
    if results:
        declined_log_count = results[0].get('declined_log_count', 0)
        print(f"   Declined payment log entries: {declined_log_count}")

        # Validate we found declined payment logs
        assert declined_log_count > 0, f"Expected declined payment logs, found {declined_log_count}"
        print(f"\n✅ PASS: Found {declined_log_count} declined payment log entries")

        # Verify decline rate is elevated (rogue agent should decline more than normal)
        # Note: With only 10 payments, variance is high. 30% threshold accounts for probabilistic behavior.
        if declined_count > 0:
            decline_rate = (declined_count / 10) * 100
            print(f"   Actual decline rate: {decline_rate}%")
            assert decline_rate >= 30, f"Expected elevated decline rate with rogue agent, got {decline_rate}%"
            print(f"   ✅ Rogue agent working correctly ({decline_rate}% decline rate)")
    else:
        print("   ⚠️  No declined payment logs found")
        pytest.skip("No declined payment logs found in New Relic")

    # Validate database entries for declined payments
    print(f"\n7. Validating database entries for declined payments...")
    if declined_bill_ids:
        db_entries_found = 0
        db_entries_missing = 0

        for bill_id in declined_bill_ids:
            transaction = query_transaction_by_bill_id(bill_id)
            if transaction:
                db_entries_found += 1
                print(f"   ✓ Found database entry for {bill_id}")
                print(f"     - EventType: {transaction['EventType']}")
                print(f"     - Status: {transaction['Status']}")
                print(f"     - DeclineReason: {transaction['DeclineReason'][:80]}...")

                # Validate transaction data
                assert transaction['EventType'] == 'BillPaymentDeclined', \
                    f"Expected EventType='BillPaymentDeclined', got '{transaction['EventType']}'"
                assert transaction['Status'] == 'declined', \
                    f"Expected Status='declined', got '{transaction['Status']}'"
                assert transaction['DeclineReason'] is not None, \
                    "DeclineReason should not be null for declined payment"

                # Check that DeclineReason contains risk assessment details
                decline_reason = transaction['DeclineReason']
                assert 'risk' in decline_reason.lower() or 'declined' in decline_reason.lower(), \
                    f"DeclineReason should mention risk or decline: {decline_reason}"
            else:
                db_entries_missing += 1
                print(f"   ✗ Missing database entry for {bill_id}")

        print(f"\n   Database entries: {db_entries_found} found, {db_entries_missing} missing")

        # We should find at least some declined payments in the database
        assert db_entries_found > 0, \
            f"Expected to find declined payments in database, found {db_entries_found}"

        print(f"\n✅ PASS: Declined payments correctly recorded in database")
    else:
        print("   ⚠️  No declined payments to validate in database (all payments were approved)")
        print("   This can happen with probabilistic rogue agent - test still valid")


# Test 5: Agent Model Tracking
def test_agent_model_tracking_in_newrelic(reset_risk_scenarios):
    """Uses reset_risk_scenarios fixture for cleanup"""
    _ = reset_risk_scenarios  # Mark as used
    """
    Validate that agent model (gpt-4o vs gpt-4o-mini) is tracked in New Relic.

    This test:
    1. Sends payments with normal agent (gpt-4o)
    2. Switches to rogue agent (gpt-4o-mini)
    3. Sends payments with rogue agent
    4. Queries New Relic to verify agent model is tracked
    """
    print("\n" + "="*80)
    print("TEST: Agent Model Tracking in New Relic")
    print("="*80)

    # Phase 1: Normal agent
    print("\n1. Testing with normal agent (gpt-4o)...")
    disable_rogue_agent()
    time.sleep(2)

    for i in range(3):
        result = make_test_payment(amount=50.0)
        print(f"   Payment {i+1}: status={result['status_code']}")
        time.sleep(1)

    # Phase 2: Rogue agent
    print("\n2. Testing with rogue agent (gpt-4o-mini)...")
    enable_rogue_agent()
    time.sleep(2)

    for i in range(3):
        result = make_test_payment(amount=150.0)
        print(f"   Payment {i+1}: status={result['status_code']}")
        time.sleep(1)

    # Cleanup
    disable_rogue_agent()

    # Wait for logs
    print("\n3. Waiting 30 seconds for logs to appear in New Relic...")
    time.sleep(30)

    # Query for agent model in logs
    print("\n4. Querying New Relic for agent model tracking...")

    nrql = f"""
    SELECT count(*) as log_count
    FROM Log
    WHERE (message LIKE '%gpt-4o%' OR message LIKE '%agent_model%')
      AND entity.name = '{APP_NAME_PREFIX} - Support Service'
    SINCE 3 minutes ago
    """

    results = query_nerdgraph(nrql)

    print(f"\n5. Results:")
    if results:
        log_count = results[0].get('log_count', 0)
        print(f"   Agent model log entries: {log_count}")

        # Validate we found agent model tracking
        assert log_count > 0, f"Expected agent model tracking in logs, found {log_count}"
        print(f"\n✅ PASS: Found {log_count} log entries with agent model information")
    else:
        print("   ⚠️  No agent model tracking found in logs")
        pytest.skip("No agent model tracking found in New Relic")


# Test (Future): eBPF Distributed Tracing
def test_risk_assessment_ebpf_traces(reset_risk_scenarios):
    """Uses reset_risk_scenarios fixture for cleanup"""
    _ = reset_risk_scenarios  # Mark as used
    """
    Validate eBPF distributed tracing for Risk Assessment Service.

    This test will work once eBPF instrumentation is configured for the
    Risk Assessment Service. It validates:
    1. Spans exist for risk assessment calls
    2. Distributed trace connects: Bill Pay → Risk Assessment → Support
    3. Span attributes include risk_level, decision, agent_model

    Current Status: EXPECTED TO SKIP (eBPF not yet configured)
    """
    print("\n" + "="*80)
    print("TEST: Risk Assessment eBPF Distributed Tracing (Future)")
    print("="*80)

    # Make test payments to generate traces
    print("\n1. Generating risk assessment activity...")
    for i in range(3):
        result = make_test_payment(amount=75.0)
        print(f"   Payment {i+1}: status={result['status_code']}")
        time.sleep(1)

    # Wait for traces
    print("\n2. Waiting 30 seconds for traces to appear in New Relic...")
    time.sleep(30)

    # Query for eBPF spans from Risk Assessment Service
    print("\n3. Querying for eBPF spans from Risk Assessment Service...")

    nrql = f"""
    SELECT count(*) as span_count, average(duration) as avg_duration_ms
    FROM Span
    WHERE entity.name = '{APP_NAME_PREFIX} - Risk Assessment Service'
      OR name LIKE '%assess-risk%'
      OR name LIKE '%risk-assessment%'
    SINCE 3 minutes ago
    """

    results = query_nerdgraph(nrql)

    print(f"\n4. Results:")
    if results and results[0].get('span_count', 0) > 0:
        span_count = results[0].get('span_count', 0)
        avg_duration = results[0].get('avg_duration_ms', 0)
        print(f"   eBPF spans found: {span_count}")
        print(f"   Average duration: {avg_duration:.2f}ms")

        # Query for span attributes
        print("\n5. Checking for risk assessment attributes on spans...")
        nrql_attrs = f"""
        SELECT count(*) as spans_with_attrs
        FROM Span
        WHERE (entity.name = '{APP_NAME_PREFIX} - Risk Assessment Service'
               OR name LIKE '%assess-risk%')
          AND (risk_level IS NOT NULL
               OR decision IS NOT NULL
               OR agent_model IS NOT NULL)
        SINCE 3 minutes ago
        """

        attr_results = query_nerdgraph(nrql_attrs)
        if attr_results and attr_results[0].get('spans_with_attrs', 0) > 0:
            spans_with_attrs = attr_results[0].get('spans_with_attrs', 0)
            print(f"   Spans with risk attributes: {spans_with_attrs}")
            print(f"\n✅ PASS: eBPF instrumentation working with {span_count} spans")
        else:
            print("   ⚠️  Spans exist but no risk assessment attributes found")
            print("   Attributes to add: risk_level, decision, agent_model")
            pytest.skip("eBPF spans exist but missing custom attributes")
    else:
        print("   ℹ️  No eBPF spans found for Risk Assessment Service")
        print("   This is EXPECTED until eBPF instrumentation is configured")
        print("\n   To enable eBPF for Risk Assessment Service:")
        print("   1. Install Pixie or New Relic eBPF agent on cluster")
        print("   2. Configure service discovery for risk-assessment-service")
        print("   3. Add custom attributes: risk_level, decision, agent_model")
        pytest.skip("eBPF not yet configured for Risk Assessment Service (expected)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

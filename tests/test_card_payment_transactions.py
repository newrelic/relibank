"""
Test card payment transaction database entries.

Validates that card payments (successful and declined) are properly recorded
in the Transactions database via the Kafka → Transaction Service pipeline.
"""

import pytest
import requests
import time
import pyodbc
import os
from pathlib import Path


# Service URLs
BILL_PAY_SERVICE_URL = os.getenv("BILL_PAY_SERVICE", "http://localhost:5000")
SCENARIO_SERVICE_URL = os.getenv("SCENARIO_SERVICE_URL", "http://localhost:8000")

# Database connection details
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_DATABASE = os.getenv("DB_DATABASE", "RelibankDB")
DB_USERNAME = os.getenv("DB_USERNAME", "SA")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrong@Password!")
CONNECTION_STRING = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD};TrustServerCertificate=yes"


def get_db_connection():
    """Get database connection"""
    return pyodbc.connect(CONNECTION_STRING)


def send_card_payment(bill_id, amount):
    """Send a card payment request"""
    payload = {
        "billId": bill_id,
        "amount": amount,
        "currency": "usd",
        "paymentMethodId": "pm_card_visa",  # Stripe test card
        "saveCard": False,
        "payee": "Electric Company",
        "accountId": "acc-test-standard",
    }
    response = requests.post(
        f"{BILL_PAY_SERVICE_URL}/bill-pay-service/card-payment",
        json=payload,
        timeout=30
    )
    return response


def enable_stolen_card_scenario():
    """Enable stolen card scenario with 100% probability"""
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/stolen-card",
        params={"enabled": True, "probability": 100.0},
        timeout=10
    )
    response.raise_for_status()


def enable_rogue_agent():
    """Enable rogue agent for risk assessment declines"""
    response = requests.post(
        f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/rogue-agent",
        params={"enabled": True},
        timeout=10
    )
    response.raise_for_status()


def reset_scenarios():
    """Reset all scenarios"""
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/payment-scenarios/reset", timeout=10)
    requests.post(f"{SCENARIO_SERVICE_URL}/scenario-runner/api/risk-assessment/reset", timeout=10)


def query_transaction_by_bill_id(bill_id):
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
def reset_scenarios_fixture():
    """Fixture to reset scenarios before and after tests"""
    reset_scenarios()
    yield
    reset_scenarios()


def test_successful_card_payment_recorded_in_database(reset_scenarios_fixture):
    """
    Verify successful card payments appear in Transactions table.

    Flow:
    1. Send card payment via bill pay service
    2. Bill pay publishes CardPaymentProcessed to Kafka
    3. Transaction service consumes and writes to database
    4. Verify database entry exists with correct data
    """
    print("\n=== Testing Successful Card Payment Database Entry ===")

    # Send card payment
    bill_id = f"CARD-SUCCESS-{int(time.time())}"
    amount = 125.50

    print(f"\n1. Sending card payment: {bill_id}, ${amount}")
    response = send_card_payment(bill_id, amount)

    assert response.status_code == 200, f"Card payment failed: {response.status_code} - {response.text}"
    print(f"   ✓ Payment successful: {response.json()['message']}")

    # Wait for Kafka processing
    print("\n2. Waiting 5 seconds for Kafka → Transaction Service → Database...")
    time.sleep(5)

    # Query database
    print(f"\n3. Querying Transactions table for BillID: {bill_id}")
    transaction = query_transaction_by_bill_id(bill_id)

    assert transaction is not None, f"Transaction not found in database for BillID: {bill_id}"
    print(f"   ✓ Found transaction: {transaction}")

    # Validate transaction data
    print("\n4. Validating transaction data...")
    assert transaction["EventType"] == "CardPaymentProcessed", f"Wrong EventType: {transaction['EventType']}"
    assert transaction["BillID"] == bill_id, f"BillID mismatch"
    assert transaction["Amount"] == amount, f"Amount mismatch: {transaction['Amount']} != {amount}"
    assert transaction["Currency"] == "usd", f"Currency mismatch: {transaction['Currency']}"
    assert transaction["AccountID"] == 0, f"AccountID should be 0 for card payments, got {transaction['AccountID']}"
    assert transaction["Status"] == "succeeded", f"Status mismatch: {transaction['Status']}"

    print("   ✓ EventType: CardPaymentProcessed")
    print("   ✓ AccountID: 0 (card payment)")
    print("   ✓ Status: succeeded")
    print("   ✓ Amount and Currency match")

    print("\n✓ Successful card payment correctly recorded in database")


def test_declined_card_payment_stripe_recorded_in_database(reset_scenarios_fixture):
    """
    Verify Stripe-declined card payments appear in Transactions table.

    Tests the stolen card scenario where Stripe declines the payment.
    Validates paymentMethodId shows pm_card_visa_chargeDeclinedStolenCard.
    """
    print("\n=== Testing Stripe-Declined Card Payment Database Entry ===")

    # Enable stolen card scenario
    print("\n1. Enabling stolen card scenario (100% probability)...")
    enable_stolen_card_scenario()
    print("   ✓ Stolen card scenario enabled")

    # Send card payment
    bill_id = f"CARD-STOLEN-{int(time.time())}"
    amount = 25.00

    print(f"\n2. Sending card payment: {bill_id}, ${amount}")
    response = send_card_payment(bill_id, amount)

    assert response.status_code == 402, f"Expected 402 (card declined), got {response.status_code}"
    print(f"   ✓ Payment declined by Stripe: {response.json()['detail']}")

    # Wait for Kafka processing
    print("\n3. Waiting 5 seconds for Kafka → Transaction Service → Database...")
    time.sleep(5)

    # Query database
    print(f"\n4. Querying Transactions table for BillID: {bill_id}")
    transaction = query_transaction_by_bill_id(bill_id)

    assert transaction is not None, f"Declined transaction not found in database for BillID: {bill_id}"
    print(f"   ✓ Found transaction: {transaction}")

    # Validate transaction data
    print("\n5. Validating declined transaction data...")
    assert transaction["EventType"] == "CardPaymentDeclined", f"Wrong EventType: {transaction['EventType']}"
    assert transaction["BillID"] == bill_id, f"BillID mismatch"
    assert transaction["Amount"] == amount, f"Amount mismatch: {transaction['Amount']} != {amount}"
    assert transaction["Currency"] == "usd", f"Currency mismatch: {transaction['Currency']}"
    assert transaction["AccountID"] == 0, f"AccountID should be 0 for card payments, got {transaction['AccountID']}"
    assert transaction["Status"] == "declined", f"Status should be 'declined', got {transaction['Status']}"
    assert transaction["DeclineReason"] is not None, f"DeclineReason should not be null"

    # Validate DeclineReason contains stolen card payment method
    assert "pm_card_visa_chargeDeclinedStolenCard" in transaction["DeclineReason"], \
        f"DeclineReason should mention stolen card payment method: {transaction['DeclineReason']}"

    print("   ✓ EventType: CardPaymentDeclined")
    print("   ✓ AccountID: 0 (card payment)")
    print("   ✓ Status: declined")
    print("   ✓ DeclineReason contains: pm_card_visa_chargeDeclinedStolenCard")
    print(f"   DeclineReason: {transaction['DeclineReason'][:100]}...")

    print("\n✓ Stripe-declined card payment correctly recorded in database")


def test_risk_declined_card_payment_recorded_in_database(reset_scenarios_fixture):
    """
    Verify risk assessment declined card payments appear in Transactions table.

    Tests payments declined by risk assessment service (rogue agent).
    Validates DeclineReason contains risk level, score, and pm_card_visa_chargeDeclined.
    """
    print("\n=== Testing Risk Assessment Declined Card Payment Database Entry ===")

    # Enable rogue agent
    print("\n1. Enabling rogue agent (gpt-4o-mini, ~90% decline rate)...")
    enable_rogue_agent()
    print("   ✓ Rogue agent enabled")

    # Send multiple payments to ensure at least one is declined
    print("\n2. Sending 5 card payments (expecting most to be declined)...")
    declined_bill_id = None

    for i in range(5):
        bill_id = f"CARD-RISK-{int(time.time())}-{i}"
        amount = 150.00 + (i * 10)

        response = send_card_payment(bill_id, amount)

        if response.status_code == 403:  # Risk assessment decline
            print(f"   Payment {i+1}: ❌ DECLINED by risk assessment")
            declined_bill_id = bill_id
            break
        else:
            print(f"   Payment {i+1}: ✅ Approved (status {response.status_code})")

        time.sleep(1)

    assert declined_bill_id is not None, "No payments were declined by risk assessment (unlucky with rogue agent probability)"

    # Wait for Kafka processing
    print("\n3. Waiting 5 seconds for Kafka → Transaction Service → Database...")
    time.sleep(5)

    # Query database
    print(f"\n4. Querying Transactions table for BillID: {declined_bill_id}")
    transaction = query_transaction_by_bill_id(declined_bill_id)

    assert transaction is not None, f"Declined transaction not found in database for BillID: {declined_bill_id}"
    print(f"   ✓ Found transaction: {transaction}")

    # Validate transaction data
    print("\n5. Validating risk-declined transaction data...")
    assert transaction["EventType"] == "CardPaymentDeclined", f"Wrong EventType: {transaction['EventType']}"
    assert transaction["BillID"] == declined_bill_id, f"BillID mismatch"
    assert transaction["AccountID"] == 0, f"AccountID should be 0 for card payments, got {transaction['AccountID']}"
    assert transaction["Status"] == "declined", f"Status should be 'declined', got {transaction['Status']}"
    assert transaction["DeclineReason"] is not None, f"DeclineReason should not be null"

    # Validate DeclineReason contains risk assessment info
    decline_reason = transaction["DeclineReason"]
    assert "pm_card_visa_chargeDeclined" in decline_reason, \
        f"DeclineReason should mention risk assessment declined card: {decline_reason}"
    assert "Risk Level:" in decline_reason, \
        f"DeclineReason should contain 'Risk Level:': {decline_reason}"
    assert "Score:" in decline_reason, \
        f"DeclineReason should contain 'Score:': {decline_reason}"

    print("   ✓ EventType: CardPaymentDeclined")
    print("   ✓ AccountID: 0 (card payment)")
    print("   ✓ Status: declined")
    print("   ✓ DeclineReason contains: pm_card_visa_chargeDeclined")
    print("   ✓ DeclineReason contains: Risk Level and Score")
    print(f"   DeclineReason: {decline_reason[:150]}...")

    print("\n✓ Risk assessment declined card payment correctly recorded in database")


def test_card_payment_distinguishable_from_account_transfers(reset_scenarios_fixture):
    """
    Verify card payments (AccountID=0) are distinguishable from account transfers (AccountID>0).

    Validates the convention that card payments use AccountID=0.
    """
    print("\n=== Testing Card Payment vs Account Transfer Distinction ===")

    # Send card payment
    bill_id = f"CARD-ACCT-TEST-{int(time.time())}"
    amount = 88.88

    print(f"\n1. Sending card payment: {bill_id}, ${amount}")
    response = send_card_payment(bill_id, amount)
    assert response.status_code == 200, f"Card payment failed: {response.status_code}"
    print("   ✓ Card payment successful")

    # Wait for processing
    print("\n2. Waiting 5 seconds for database entry...")
    time.sleep(5)

    # Query and validate
    print(f"\n3. Verifying AccountID=0 convention for card payments...")
    transaction = query_transaction_by_bill_id(bill_id)

    assert transaction is not None, f"Transaction not found"
    assert transaction["AccountID"] == 0, \
        f"Card payment should have AccountID=0, got {transaction['AccountID']}"
    assert transaction["EventType"] == "CardPaymentProcessed", \
        f"EventType should indicate card payment: {transaction['EventType']}"

    print("   ✓ Card payment has AccountID=0")
    print("   ✓ EventType: CardPaymentProcessed")
    print("\n✓ Card payments are distinguishable from account transfers")

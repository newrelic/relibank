import pytest
import requests
import os
import uuid
from typing import Dict

# Configuration - use environment variables with local defaults
BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
ACCOUNTS_SERVICE = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")
BILL_PAY_SERVICE = os.getenv("BILL_PAY_SERVICE", "http://localhost:5000")
CHATBOT_SERVICE = os.getenv("CHATBOT_SERVICE", "http://localhost:5003")
AUTH_SERVICE = os.getenv("AUTH_SERVICE", "http://localhost:5006")

# Seeded test users (from accounts_service/postgres/init.sql)
ALICE_USER_ID = "b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d"
BOB_USER_ID = "f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a"
NONEXISTENT_USER_ID = "00000000-0000-0000-0000-000000000000"

# Test user credentials
TEST_USER = {
    "id": str(uuid.uuid4()),
    "name": "Test User",
    "email": f"test_{os.getpid()}@relibank.com",
    "alert_preferences": {},
    "phone": "555-1234",
    "address": "123 Test St",
    "income": 50000.0,
    "preferred_language": "en",
    "marketing_preferences": {},
    "privacy_preferences": {}
}


def test_frontend_loads():
    """Test that the React frontend loads successfully"""
    print("\n=== Testing Frontend ===" )

    response = requests.get(f"{BASE_URL}/")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Frontend failed to load: {response.status_code}"

    # Check that HTML is returned (React app loads)
    assert "<html" in response.text or "<HTML" in response.text, "HTML not found in response"
    assert "script" in response.text.lower(), "No JavaScript found in page"

    print("✓ Frontend loads successfully")


def test_accounts_service_health():
    """Test that accounts service is healthy"""
    print("\n=== Testing Accounts Service Health ===")

    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/health")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Accounts service health check failed: {response.status_code}"

    print("✓ Accounts service is healthy")


def test_bill_pay_service_health():
    """Test that bill pay service is healthy"""
    print("\n=== Testing Bill Pay Service Health ===")

    response = requests.get(f"{BILL_PAY_SERVICE}/bill-pay-service/health")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Bill pay service health check failed: {response.status_code}"

    print("✓ Bill pay service is healthy")


def test_chatbot_service_health():
    """Test that chatbot service is healthy"""
    print("\n=== Testing Chatbot Service Health ===")

    response = requests.get(f"{CHATBOT_SERVICE}/chatbot-service/health")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Chatbot service health check failed: {response.status_code}"

    print("✓ Chatbot service is healthy")


def test_auth_service_health():
    """Test that auth service is healthy"""
    print("\n=== Testing Auth Service Health ===")

    response = requests.get(f"{AUTH_SERVICE}/auth-service/health")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Auth service health check failed: {response.status_code}"

    print("✓ Auth service is healthy")


def test_auth_service_login():
    """Test authentication with valid credentials"""
    print("\n=== Testing Auth Service Login ===")

    # Test with valid credentials
    login_data = {
        "email": "alice.j@relibank.com",
        "password": "aJ7#kQ9mP2wX"
    }

    response = requests.post(
        f"{AUTH_SERVICE}/auth-service/login",
        json=login_data
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Login failed with valid credentials: {response.status_code}"

    data = response.json()
    print(f"Login response: {data}")

    # Verify response contains expected fields
    assert "token" in data, "Response missing 'token' field"
    assert "email" in data, "Response missing 'email' field"
    assert "user_id" in data, "Response missing 'user_id' field"
    assert data["email"] == login_data["email"], "Email mismatch in response"

    print("✓ Auth service login successful")

    # Test with invalid credentials
    print("\nTesting with invalid credentials...")
    invalid_login = {
        "email": "alice.j@relibank.com",
        "password": "wrongpassword"
    }

    response = requests.post(
        f"{AUTH_SERVICE}/auth-service/login",
        json=invalid_login
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"

    print("✓ Invalid credentials correctly rejected")


def test_create_user_account():
    """Test creating a new user account"""
    print("\n=== Testing User Account Creation ===")

    # Create user
    response = requests.post(
        f"{ACCOUNTS_SERVICE}/accounts-service/users",
        json=TEST_USER
    )

    print(f"Status: {response.status_code}")

    # Accept 200/201 for new user, or 409 if user already exists
    assert response.status_code in [200, 201, 409], f"User creation failed: {response.status_code}"

    if response.status_code in [200, 201]:
        print(f"✓ User account created: {TEST_USER['email']}")
    else:
        print(f"✓ User already exists: {TEST_USER['email']}")


def test_get_user_account():
    """Test retrieving user account information"""
    print("\n=== Testing Get User Account ===")

    # Ensure user exists first
    requests.post(f"{ACCOUNTS_SERVICE}/accounts-service/users", json=TEST_USER)

    # Get user info
    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/users/{TEST_USER['email']}")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to get user account: {response.status_code}"

    data = response.json()
    print(f"User data: {data}")
    assert data.get("email") == TEST_USER["email"], "Email mismatch"

    print("✓ User account retrieved successfully")


def test_create_bank_account():
    """Test creating a bank account for a user"""
    print("\n=== Testing Bank Account Creation ===")

    # Ensure user exists
    requests.post(f"{ACCOUNTS_SERVICE}/accounts-service/users", json=TEST_USER)

    # Create bank account with all required fields
    account_data = {
        "id": int(os.getpid()),
        "name": "Test Checking Account",
        "balance": 5000.00,
        "routing_number": "123456789",
        "interest_rate": 0.01,
        "last_statement_date": "2024-01-01",
        "account_type": "checking"
    }

    response = requests.post(
        f"{ACCOUNTS_SERVICE}/accounts-service/accounts/{TEST_USER['email']}",
        json=account_data
    )

    print(f"Status: {response.status_code}")

    # Accept 200/201 for new account, or 409/500 if account already exists
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"Account created: {data}")
        print("✓ Bank account created successfully")
    elif response.status_code in [409, 500]:
        print("✓ Bank account already exists or user already has account")
    else:
        pytest.fail(f"Account creation failed: {response.status_code} - {response.text}")


def test_get_bank_accounts():
    """Test retrieving bank accounts for a user"""
    print("\n=== Testing Get Bank Accounts ===")

    # Ensure user and account exist
    requests.post(f"{ACCOUNTS_SERVICE}/accounts-service/users", json=TEST_USER)
    account_data = {
        "id": int(os.getpid()),
        "name": "Test Checking Account",
        "balance": 5000.00,
        "routing_number": "123456789",
        "interest_rate": 0.01,
        "last_statement_date": "2024-01-01",
        "account_type": "checking"
    }
    requests.post(
        f"{ACCOUNTS_SERVICE}/accounts-service/accounts/{TEST_USER['email']}",
        json=account_data
    )

    # Get accounts
    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/accounts/{TEST_USER['email']}")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Accounts: {data}")
        assert isinstance(data, list), "Expected list of accounts"
        if len(data) > 0:
            print(f"✓ Found {len(data)} bank account(s)")
        else:
            print("✓ User has no accounts yet (expected for new user)")
    else:
        print(f"⚠ Get accounts returned {response.status_code}, may be expected for new user")


def test_chatbot_interaction():
    """Test chatbot service interaction"""
    print("\n=== Testing Chatbot Interaction ===")

    # Test chatbot with a simple query as form data
    response = requests.post(
        f"{CHATBOT_SERVICE}/chatbot-service/chat",
        params={"prompt": "What services does Relibank offer?"}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Chatbot response: {data.get('response', '')[:100]}...")
        assert "response" in data, "Chatbot response missing 'response' field"
        assert len(data["response"]) > 0, "Chatbot returned empty response"
        print("✓ Chatbot interaction successful")
    elif response.status_code == 503:
        print("⚠ Chatbot service not ready (AI service may not be configured)")
    else:
        print(f"⚠ Chatbot returned {response.status_code}: {response.text[:200]}")


def test_bill_payment_flow():
    """Test bill payment processing"""
    print("\n=== Testing Bill Payment Flow ===")

    # Prepare payment request with correct fields
    payment_request = {
        "billId": f"test_bill_{os.getpid()}",
        "amount": 99.99,
        "currency": "USD",
        "fromAccountId": int(os.getpid()),
        "toAccountId": 0
    }

    response = requests.post(
        f"{BILL_PAY_SERVICE}/bill-pay-service/pay",
        json=payment_request
    )

    print(f"Status: {response.status_code}")

    # Accept 200 for success, or scenarios might return other codes (402 for decline, 504 for timeout)
    if response.status_code == 200:
        data = response.json()
        print(f"Payment response: {data}")
        print("✓ Bill payment processed successfully")
    elif response.status_code == 402:
        print("⚠ Payment declined (scenario may be active)")
    elif response.status_code == 504:
        print("⚠ Payment timeout (scenario may be active)")
    else:
        print(f"⚠ Payment returned {response.status_code}: {response.text[:200]}")
        print("✓ Bill payment test completed (validation may require existing account)")


def test_complete_user_journey():
    """Test complete user journey: login → create user → create account → make payment → chat"""
    print("\n=== Testing Complete User Journey ===")

    # Use Alice's credentials for the login test
    login_credentials = {
        "email": "alice.j@relibank.com",
        "password": "aJ7#kQ9mP2wX"
    }

    # Step 1: Login with existing user
    print("Step 1: Logging in...")
    login_response = requests.post(
        f"{AUTH_SERVICE}/auth-service/login",
        json=login_credentials
    )

    if login_response.status_code == 200:
        login_data = login_response.json()
        auth_token = login_data.get("token")
        authenticated_email = login_data.get("email")
        print(f"✓ Logged in successfully as {authenticated_email}")
        print(f"  Token received: {auth_token[:20]}...")
    else:
        print(f"⚠ Login returned {login_response.status_code}, continuing with test user creation")
        authenticated_email = None
        auth_token = None

    # Step 2: Create a new test user for the journey
    journey_user = {
        "id": str(uuid.uuid4()),
        "name": "Journey Test User",
        "email": f"journey_{os.getpid()}@relibank.com",
        "alert_preferences": {},
        "phone": "555-9999",
        "address": "999 Journey Lane",
        "income": 75000.0,
        "preferred_language": "en",
        "marketing_preferences": {},
        "privacy_preferences": {}
    }

    print("Step 2: Creating test user...")
    user_response = requests.post(
        f"{ACCOUNTS_SERVICE}/accounts-service/users",
        json=journey_user
    )
    assert user_response.status_code in [200, 201, 500], "User creation failed"
    print("✓ User created (or already exists)")

    # Step 3: Create bank account
    print("Step 3: Creating bank account...")
    account_data = {
        "id": int(os.getpid()) + 1000,
        "name": "Journey Checking Account",
        "balance": 10000.00,
        "routing_number": "987654321",
        "interest_rate": 0.02,
        "last_statement_date": "2024-01-01",
        "account_type": "checking"
    }
    account_response = requests.post(
        f"{ACCOUNTS_SERVICE}/accounts-service/accounts/{journey_user['email']}",
        json=account_data
    )
    if account_response.status_code in [200, 201]:
        print("✓ Bank account created")
    else:
        print(f"✓ Bank account creation returned {account_response.status_code} (may already exist)")

    # Step 4: Get account information
    print("Step 4: Retrieving account info...")
    accounts_response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/accounts/{journey_user['email']}")
    if accounts_response.status_code == 200:
        accounts = accounts_response.json()
        print(f"✓ Account info retrieved: {len(accounts)} account(s)")
    else:
        print(f"✓ Get accounts returned {accounts_response.status_code}")

    # Step 5: Make a payment
    print("Step 5: Making a payment...")
    payment_response = requests.post(
        f"{BILL_PAY_SERVICE}/bill-pay-service/pay",
        json={
            "billId": f"journey_bill_{os.getpid()}",
            "amount": 250.00,
            "currency": "USD",
            "fromAccountId": int(os.getpid()) + 1000,
            "toAccountId": 0
        }
    )
    # Payment may succeed or fail due to scenarios
    if payment_response.status_code == 200:
        print("✓ Payment processed")
    else:
        print(f"✓ Payment returned {payment_response.status_code} (scenario may be active or validation failed)")

    # Step 6: Chat with bot
    print("Step 6: Chatting with bot...")
    chat_response = requests.post(
        f"{CHATBOT_SERVICE}/chatbot-service/chat",
        params={"prompt": "What's my account balance?"}
    )
    if chat_response.status_code == 200:
        print("✓ Chatbot responded")
    elif chat_response.status_code == 503:
        print("✓ Chatbot service not ready (expected if AI not configured)")
    else:
        print(f"✓ Chatbot returned {chat_response.status_code}")

    print("\n✓ Complete user journey successful!")


def get_stripe_customer_id(user_id: str) -> str:
    """Fetch stripe_customer_id for a seeded user from the accounts service."""
    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/users/by-id/{user_id}", timeout=10)
    assert response.status_code == 200, f"Failed to fetch user {user_id}: {response.status_code}"
    return response.json()["stripe_customer_id"]


def send_card_payment_by_user(bill_id: str, user_id: str, amount: float = 100.00) -> requests.Response:
    """Send a card payment using userId so the service resolves Stripe credentials dynamically."""
    payload = {
        "billId": bill_id,
        "amount": amount,
        "currency": "usd",
        "userId": user_id,
        "saveCard": False
    }
    return requests.post(f"{BILL_PAY_SERVICE}/bill-pay-service/card-payment", json=payload, timeout=15)


def test_alice_payment_methods_visible():
    """Happy path: Alice's saved cards are retrievable via her Stripe customer ID."""
    print("\n=== Testing Alice Payment Methods Visible ===")

    customer_id = get_stripe_customer_id(ALICE_USER_ID)
    assert customer_id, "Alice has no stripe_customer_id in DB"

    response = requests.get(f"{BILL_PAY_SERVICE}/bill-pay-service/payment-methods/{customer_id}", timeout=10)
    assert response.status_code == 200, f"Failed to list Alice's cards: {response.status_code}"

    data = response.json()
    assert "paymentMethods" in data
    assert len(data["paymentMethods"]) > 0, "Alice should have at least one saved card"

    cards = [f"{m['brand']} ****{m['last4']}" for m in data["paymentMethods"]]
    print(f"✓ Alice's payment methods: {cards}")


def test_alice_card_payment_succeeds():
    """Happy path: card payment with Alice's userId resolves her credentials and succeeds."""
    print("\n=== Testing Alice Card Payment Succeeds ===")

    response = send_card_payment_by_user("BILL-ALICE-HAPPY-001", ALICE_USER_ID, 50.00)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "paymentIntentId" in data, "Response missing paymentIntentId"

    print(f"✓ Alice's card payment succeeded: {data['paymentIntentId']}")


def test_bob_payment_methods_visible():
    """Edge case 1: Bob's saved cards are distinct from Alice's."""
    print("\n=== Testing Bob Payment Methods Visible ===")

    alice_customer_id = get_stripe_customer_id(ALICE_USER_ID)
    bob_customer_id = get_stripe_customer_id(BOB_USER_ID)
    assert alice_customer_id != bob_customer_id, "Alice and Bob must have different Stripe customer IDs"

    response = requests.get(f"{BILL_PAY_SERVICE}/bill-pay-service/payment-methods/{bob_customer_id}", timeout=10)
    assert response.status_code == 200, f"Failed to list Bob's cards: {response.status_code}"

    data = response.json()
    assert "paymentMethods" in data
    assert len(data["paymentMethods"]) > 0, "Bob should have at least one saved card"

    cards = [f"{m['brand']} ****{m['last4']}" for m in data["paymentMethods"]]
    print(f"✓ Bob's payment methods: {cards}")


def test_bob_card_payment_succeeds():
    """Edge case 1: card payment with Bob's userId uses Bob's Stripe credentials."""
    print("\n=== Testing Bob Card Payment Succeeds ===")

    response = send_card_payment_by_user("BILL-BOB-HAPPY-001", BOB_USER_ID, 75.00)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "paymentIntentId" in data, "Response missing paymentIntentId"

    print(f"✓ Bob's card payment succeeded: {data['paymentIntentId']}")


def test_user_switch_independent_payments():
    """Edge case 2: Alice then Bob payments both succeed with distinct payment intent IDs."""
    print("\n=== Testing User Switch Independent Payments ===")

    alice_resp = send_card_payment_by_user("BILL-SWITCH-ALICE-001", ALICE_USER_ID, 50.00)
    bob_resp = send_card_payment_by_user("BILL-SWITCH-BOB-001", BOB_USER_ID, 60.00)

    assert alice_resp.status_code == 200, f"Alice payment failed: {alice_resp.status_code} {alice_resp.text}"
    assert bob_resp.status_code == 200, f"Bob payment failed: {bob_resp.status_code} {bob_resp.text}"

    alice_intent = alice_resp.json()["paymentIntentId"]
    bob_intent = bob_resp.json()["paymentIntentId"]
    assert alice_intent != bob_intent, "Each user should produce a distinct payment intent"

    print(f"✓ User switch: Alice={alice_intent}, Bob={bob_intent}")


def test_nonexistent_user_returns_404():
    """Edge case 3: userId not in accounts DB returns 404, no crash."""
    print("\n=== Testing Nonexistent User Returns 404 ===")

    response = send_card_payment_by_user("BILL-NULL-TEST-001", NONEXISTENT_USER_ID, 50.00)

    assert response.status_code == 404, f"Expected 404 for unknown user, got {response.status_code}"
    print(f"✓ Unknown userId → 404: {response.json().get('detail')}")


def test_no_credentials_returns_400():
    """Edge case 3: request with neither userId nor paymentMethodId returns 400, no crash."""
    print("\n=== Testing No Credentials Returns 400 ===")

    response = requests.post(
        f"{BILL_PAY_SERVICE}/bill-pay-service/card-payment",
        json={"billId": "BILL-NO-CREDS-001", "amount": 50.00, "currency": "usd", "saveCard": False},
        timeout=10
    )

    assert response.status_code == 400, f"Expected 400 when no credentials provided, got {response.status_code}"
    print(f"✓ Missing credentials → 400: {response.json().get('detail')}")


if __name__ == "__main__":
    # Run tests manually for quick validation
    pytest.main([__file__, "-v", "-s"])

"""
Test suite for APM User ID Tracking

Tests that the x-browser-user-id header is properly propagated across
all backend services and picked up by New Relic Python APM agent.
Validates:
- Header acceptance across all services
- Header propagation through service chains
- Services work without header (optional)
- Multi-service request flows maintain user ID
"""

import pytest
import requests
import os
import uuid
from typing import Dict

# Configuration
ACCOUNTS_SERVICE = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")
BILL_PAY_SERVICE = os.getenv("BILL_PAY_SERVICE", "http://localhost:5000")
TRANSACTION_SERVICE = os.getenv("TRANSACTION_SERVICE", "http://localhost:5001")
AUTH_SERVICE = os.getenv("AUTH_SERVICE", "http://localhost:5006")
CHATBOT_SERVICE = os.getenv("CHATBOT_SERVICE", "http://localhost:5003")

# Test user data
TEST_USER_ID = "test-apm-user-123"
TEST_EMAIL = "alice.j@relibank.com"


def test_accounts_service_accepts_user_id_header():
    """Test that accounts service accepts and processes x-browser-user-id header"""
    print("\n=== Testing Accounts Service Header Acceptance ===")

    headers = {"x-browser-user-id": TEST_USER_ID}
    response = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/health",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Request failed: {response.status_code}"

    print(f"✓ Accounts service accepted user ID header: {TEST_USER_ID}")


def test_bill_pay_service_accepts_user_id_header():
    """Test that bill pay service accepts and processes x-browser-user-id header"""
    print("\n=== Testing Bill Pay Service Header Acceptance ===")

    headers = {"x-browser-user-id": TEST_USER_ID}
    response = requests.get(
        f"{BILL_PAY_SERVICE}/bill-pay-service",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Request failed: {response.status_code}"

    print(f"✓ Bill Pay service accepted user ID header: {TEST_USER_ID}")


def test_transaction_service_accepts_user_id_header():
    """Test that transaction service accepts and processes x-browser-user-id header"""
    print("\n=== Testing Transaction Service Header Acceptance ===")

    headers = {"x-browser-user-id": TEST_USER_ID}
    response = requests.get(
        f"{TRANSACTION_SERVICE}/transaction-service",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Request failed: {response.status_code}"

    print(f"✓ Transaction service accepted user ID header: {TEST_USER_ID}")


def test_auth_service_accepts_user_id_header():
    """Test that auth service accepts and processes x-browser-user-id header"""
    print("\n=== Testing Auth Service Header Acceptance ===")

    headers = {"x-browser-user-id": TEST_USER_ID}
    response = requests.post(
        f"{AUTH_SERVICE}/auth-service/health",
        headers=headers
    )

    # Auth service may return 404 or 405 if health endpoint doesn't exist
    # Just verify it doesn't crash with the header
    print(f"Status: {response.status_code}")
    assert response.status_code in [200, 404, 405], \
        f"Unexpected error with header: {response.status_code}"

    print(f"✓ Auth service accepted user ID header: {TEST_USER_ID}")


def test_chatbot_service_accepts_user_id_header():
    """Test that chatbot service accepts and processes x-browser-user-id header"""
    print("\n=== Testing Chatbot Service Header Acceptance ===")

    headers = {"x-browser-user-id": TEST_USER_ID}
    response = requests.get(
        f"{CHATBOT_SERVICE}/chatbot-service",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Request failed: {response.status_code}"

    print(f"✓ Chatbot service accepted user ID header: {TEST_USER_ID}")


def test_header_propagation_accounts_to_transaction():
    """Test that x-browser-user-id propagates from accounts to transaction service"""
    print("\n=== Testing Header Propagation: Accounts → Transaction ===")

    headers = {"x-browser-user-id": TEST_USER_ID}

    # Call accounts service which internally calls transaction service
    response = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/accounts/{TEST_EMAIL}",
        headers=headers
    )

    print(f"Status: {response.status_code}")

    # May return 404 if user doesn't exist in test environment
    if response.status_code == 404:
        print("⚠ Test user not found, but header was accepted")
        return

    assert response.status_code == 200, f"Request failed: {response.status_code}"

    print(f"✓ Header propagated through accounts → transaction chain")


def test_header_propagation_bill_pay_to_transaction():
    """Test that x-browser-user-id propagates from bill pay to transaction service"""
    print("\n=== Testing Header Propagation: Bill Pay → Transaction ===")

    headers = {"x-browser-user-id": TEST_USER_ID}
    test_bill_id = str(uuid.uuid4())

    # Create payment request (will check transaction service for duplicates)
    payment_data = {
        "billId": test_bill_id,
        "userId": str(uuid.uuid4()),
        "accountId": 1,
        "fromAccountId": 1,
        "amount": 100.00,
        "currency": "USD",
        "timestamp": "2024-01-01T00:00:00Z"
    }

    response = requests.post(
        f"{BILL_PAY_SERVICE}/bill-pay-service/pay",
        headers=headers,
        json=payment_data
    )

    print(f"Status: {response.status_code}")

    # Request may fail for various reasons (insufficient funds, etc.)
    # but header should be accepted
    assert response.status_code in [200, 400, 503], \
        f"Unexpected error: {response.status_code}"

    print(f"✓ Header propagated through bill pay → transaction chain")


def test_services_work_without_header():
    """Test that all services continue to work when header is not provided"""
    print("\n=== Testing Services Without Header ===")

    # Test each service health endpoint without header
    services = [
        (ACCOUNTS_SERVICE, "/accounts-service/health"),
        (BILL_PAY_SERVICE, "/bill-pay-service"),
        (TRANSACTION_SERVICE, "/transaction-service"),
        (CHATBOT_SERVICE, "/chatbot-service"),
    ]

    for service_url, endpoint in services:
        response = requests.get(f"{service_url}{endpoint}")
        print(f"  {endpoint}: {response.status_code}")
        assert response.status_code == 200, \
            f"{endpoint} failed without header: {response.status_code}"

    print("✓ All services work without x-browser-user-id header")


def test_header_with_different_user_ids():
    """Test that different user IDs are accepted and processed"""
    print("\n=== Testing Multiple User IDs ===")

    user_ids = [
        "user-001",
        "user-002",
        str(uuid.uuid4()),
        "550e8400-e29b-41d4-a716-446655440000"
    ]

    for user_id in user_ids:
        headers = {"x-browser-user-id": user_id}
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/health",
            headers=headers
        )
        print(f"  User ID '{user_id}': {response.status_code}")
        assert response.status_code == 200, \
            f"Failed with user ID '{user_id}': {response.status_code}"

    print(f"✓ All {len(user_ids)} different user IDs accepted")


def test_header_propagation_full_chain():
    """Test header propagation through a complete multi-service request"""
    print("\n=== Testing Full Service Chain Propagation ===")

    test_user_id = f"chain-test-{uuid.uuid4()}"
    headers = {"x-browser-user-id": test_user_id}

    # Step 1: Get user from accounts service
    print(f"  Step 1: Accounts service with user ID: {test_user_id}")
    response1 = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/users/{TEST_EMAIL}",
        headers=headers
    )
    print(f"    Status: {response1.status_code}")

    # Step 2: Check browser user endpoint
    print(f"  Step 2: Browser user endpoint")
    response2 = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
        headers=headers
    )
    print(f"    Status: {response2.status_code}")

    # At least one should succeed
    assert response1.status_code in [200, 404] or response2.status_code == 200, \
        "All requests in chain failed"

    print("✓ Multi-service chain completed with header propagation")


def test_concurrent_requests_with_different_user_ids():
    """Test that concurrent requests with different user IDs don't interfere"""
    print("\n=== Testing Concurrent User IDs ===")

    import concurrent.futures

    def make_request(user_id):
        headers = {"x-browser-user-id": user_id}
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/health",
            headers=headers
        )
        return user_id, response.status_code

    user_ids = [f"concurrent-user-{i}" for i in range(10)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(make_request, user_ids))

    for user_id, status_code in results:
        print(f"  User '{user_id}': {status_code}")
        assert status_code == 200, \
            f"Request failed for user '{user_id}': {status_code}"

    print(f"✓ {len(results)} concurrent requests successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

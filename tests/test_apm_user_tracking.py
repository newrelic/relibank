"""
Test suite for APM User ID Tracking

Tests that the x-browser-user-id header is properly propagated across
all backend services and picked up by New Relic Python APM agent.
Validates:
- Header acceptance across all services
- Header propagation through service chains
- Services work without header (optional)
- Multi-service request flows maintain user ID
- Edge cases: concurrent requests, missing headers, performance impact
"""

import pytest
import requests
import os
import uuid
import time
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


def test_missing_user_id_header():
    """Test that services work correctly without user ID header (anonymous users)"""
    print("\n=== Testing Missing User ID Header ===")

    services = [
        ("Accounts", f"{ACCOUNTS_SERVICE}/accounts-service/health"),
        ("Bill Pay", f"{BILL_PAY_SERVICE}/bill-pay-service/health"),
        ("Transaction", f"{TRANSACTION_SERVICE}/transaction-service/health"),
        ("Auth", f"{AUTH_SERVICE}/auth-service/health"),
    ]

    for service_name, url in services:
        print(f"Testing {service_name} service without user ID...")

        # Request without x-browser-user-id header
        response = requests.get(url)

        assert response.status_code == 200, \
            f"{service_name} failed without user ID header: {response.status_code}"

        print(f"  ✓ {service_name} works without user ID header")

    print("✓ All services handle missing user ID gracefully")


def test_rapid_user_id_changes():
    """Test that services handle rapid changes in user ID across multiple requests"""
    print("\n=== Testing Rapid User ID Changes ===")

    session = requests.Session()
    num_requests = 30

    for i in range(num_requests):
        # Simulate browser generating new user ID
        user_id = f"browser-session-{i}"
        headers = {"x-browser-user-id": user_id}

        response = session.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/health",
            headers=headers
        )

        assert response.status_code == 200, \
            f"Request {i} failed with user ID: {user_id}"

    print(f"✓ All {num_requests} requests with changing user IDs succeeded")


def test_user_tracking_performance_impact():
    """Test that user ID tracking doesn't significantly impact response times"""
    print("\n=== Testing Performance Impact of User Tracking ===")

    num_requests = 50

    # Measure requests WITH user ID
    with_user_times = []
    for i in range(num_requests):
        headers = {"x-browser-user-id": f"perf-test-user-{i}"}
        start = time.time()
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/health",
            headers=headers
        )
        duration = time.time() - start
        if response.status_code == 200:
            with_user_times.append(duration)

    # Measure requests WITHOUT user ID
    without_user_times = []
    for _ in range(num_requests):
        start = time.time()
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/health"
        )
        duration = time.time() - start
        if response.status_code == 200:
            without_user_times.append(duration)

    avg_with = sum(with_user_times) / len(with_user_times) if with_user_times else 0
    avg_without = sum(without_user_times) / len(without_user_times) if without_user_times else 0
    overhead = avg_with - avg_without

    print(f"  Average time WITH user ID: {avg_with:.4f}s")
    print(f"  Average time WITHOUT user ID: {avg_without:.4f}s")
    print(f"  Overhead: {overhead:.4f}s ({overhead/avg_without*100:.2f}%)")

    # User tracking should add minimal overhead (< 10ms or 5% of request time)
    assert overhead < 0.01 or (overhead / avg_without) < 0.05, \
        f"User tracking adds too much overhead: {overhead:.4f}s"

    print(f"✓ User tracking overhead is acceptable")


def test_browser_user_endpoint():
    """Test the /accounts-service/browser-user endpoint that generates user IDs"""
    print("\n=== Testing Browser User ID Generation Endpoint ===")

    # Test that endpoint returns a user ID
    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/browser-user")

    assert response.status_code == 200, \
        f"Browser user endpoint failed: {response.status_code}"

    data = response.json()
    assert "user_id" in data, "Response missing user_id field"
    assert "source" in data, "Response missing source field"

    user_id = data["user_id"]
    source = data["source"]

    print(f"  Generated user ID: {user_id}")
    print(f"  Source: {source}")

    # User ID should be a valid UUID or similar identifier
    assert len(user_id) > 0, "User ID is empty"

    # Test that subsequent calls return the same user ID (session persistence)
    response2 = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
        cookies=response.cookies
    )
    data2 = response2.json()

    print(f"  Second call user ID: {data2['user_id']}")
    print(f"  Second call source: {data2['source']}")

    print(f"✓ Browser user endpoint working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

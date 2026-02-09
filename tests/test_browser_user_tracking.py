"""
Test suite for Browser User ID Tracking

Tests the new /accounts-service/browser-user endpoint that assigns user IDs
for New Relic Browser tracking. Validates:
- Random user ID assignment from database
- Header-based override with x-browser-user-id
- Invalid header fallback behavior
- UUID validation
- Response format and consistency
"""

import pytest
import requests
import os
import uuid
from typing import Dict, List

# Configuration
ACCOUNTS_SERVICE = os.getenv("ACCOUNTS_SERVICE", "http://localhost:5002")


def get_valid_user_ids(count: int = 3) -> List[str]:
    """
    Fetch valid user IDs from the database by calling the browser-user endpoint.
    Returns a list of unique user IDs.
    """
    user_ids = set()
    max_attempts = count * 10  # Try up to 10x the requested count

    for _ in range(max_attempts):
        response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/browser-user")
        if response.status_code == 200:
            data = response.json()
            user_ids.add(data["user_id"])
            if len(user_ids) >= count:
                break

    return list(user_ids)[:count]


def test_browser_user_random_assignment():
    """Test that endpoint returns a valid random user ID when no header is provided"""
    print("\n=== Testing Random User ID Assignment ===")

    response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/browser-user")

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Endpoint failed: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    # Validate response structure
    assert "user_id" in data, "Response missing 'user_id' field"
    assert "source" in data, "Response missing 'source' field"
    assert data["source"] == "random", f"Expected source='random', got '{data['source']}'"

    # Validate user_id is a valid UUID
    user_id = data["user_id"]
    try:
        uuid.UUID(user_id)
        print(f"✓ Valid UUID returned: {user_id}")
    except ValueError:
        pytest.fail(f"Invalid UUID format: {user_id}")

    print("✓ Random user ID assignment works correctly")


def test_browser_user_header_override():
    """Test that endpoint respects x-browser-user-id header when provided"""
    print("\n=== Testing Header-Based Override ===")

    # Get a valid user ID from the database
    valid_user_ids = get_valid_user_ids(count=1)
    assert len(valid_user_ids) > 0, "Failed to fetch valid user IDs from database"

    test_user_id = valid_user_ids[0]
    print(f"Using test user ID: {test_user_id}")

    headers = {"x-browser-user-id": test_user_id}

    response = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Endpoint failed: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    # Validate that the provided ID is returned
    assert data["user_id"] == test_user_id, \
        f"Expected user_id='{test_user_id}', got '{data['user_id']}'"
    assert data["source"] == "header", \
        f"Expected source='header', got '{data['source']}'"

    print(f"✓ Header override works correctly with ID: {test_user_id}")


def test_browser_user_invalid_header_fallback():
    """Test that endpoint falls back to random ID when invalid header is provided"""
    print("\n=== Testing Invalid Header Fallback ===")

    # Use a non-existent UUID
    invalid_user_id = str(uuid.uuid4())
    headers = {"x-browser-user-id": invalid_user_id}

    response = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Endpoint failed: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    # Should fall back to random selection
    assert data["source"] == "random", \
        f"Expected fallback to source='random', got '{data['source']}'"
    assert data["user_id"] != invalid_user_id, \
        "Should not return the invalid user ID"

    print(f"✓ Invalid header correctly fell back to random: {data['user_id']}")


def test_browser_user_malformed_header():
    """Test that endpoint handles malformed UUID header gracefully"""
    print("\n=== Testing Malformed Header ===")

    headers = {"x-browser-user-id": "not-a-valid-uuid"}

    response = requests.get(
        f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Endpoint failed: {response.status_code}"

    data = response.json()
    print(f"Response: {data}")

    # Should fall back to random selection
    assert data["source"] == "random", \
        f"Expected fallback to source='random', got '{data['source']}'"

    # Validate returned ID is still a valid UUID
    try:
        uuid.UUID(data["user_id"])
        print(f"✓ Malformed header handled gracefully, returned: {data['user_id']}")
    except ValueError:
        pytest.fail(f"Invalid UUID format after fallback: {data['user_id']}")


def test_browser_user_randomness():
    """Test that multiple requests return different random user IDs"""
    print("\n=== Testing Randomness ===")

    user_ids = set()
    num_requests = 10

    for i in range(num_requests):
        response = requests.get(f"{ACCOUNTS_SERVICE}/accounts-service/browser-user")
        assert response.status_code == 200
        data = response.json()
        user_ids.add(data["user_id"])

    print(f"Unique IDs from {num_requests} requests: {len(user_ids)}")
    print(f"IDs: {user_ids}")

    # With random selection, we should get some variety (not necessarily all unique)
    # This test may occasionally fail if database is very small
    assert len(user_ids) > 1, \
        "Expected some randomness in user ID selection, got same ID every time"

    print(f"✓ Randomness verified: {len(user_ids)} unique IDs")


def test_browser_user_consistency():
    """Test that same header always returns same user ID"""
    print("\n=== Testing Header Consistency ===")

    # Get a valid user ID from the database
    valid_user_ids = get_valid_user_ids(count=1)
    assert len(valid_user_ids) > 0, "Failed to fetch valid user IDs from database"

    test_user_id = valid_user_ids[0]
    print(f"Using test user ID: {test_user_id}")

    headers = {"x-browser-user-id": test_user_id}

    # Make multiple requests with same header
    for i in range(5):
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user_id, \
            f"Request {i+1}: Expected consistent user_id='{test_user_id}', got '{data['user_id']}'"

    print(f"✓ Header consistency verified across 5 requests")


def test_browser_user_multiple_valid_headers():
    """Test that different valid headers return different user IDs"""
    print("\n=== Testing Multiple Valid Headers ===")

    # Get multiple valid user IDs from the database
    valid_user_ids = get_valid_user_ids(count=3)
    assert len(valid_user_ids) >= 3, f"Failed to fetch 3 unique user IDs, only got {len(valid_user_ids)}"

    print(f"Using test user IDs: {valid_user_ids}")

    results = []
    for test_user_id in valid_user_ids:
        headers = {"x-browser-user-id": test_user_id}
        response = requests.get(
            f"{ACCOUNTS_SERVICE}/accounts-service/browser-user",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        results.append(data["user_id"])
        print(f"  Header: {test_user_id} → Response: {data['user_id']}")

    # All responses should match their respective headers
    for i, test_user_id in enumerate(valid_user_ids):
        assert results[i] == test_user_id, \
            f"Expected user_id='{test_user_id}', got '{results[i]}'"

    print("✓ Multiple valid headers handled correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""
Test microfrontend telemetry verification.

This test generates traffic to the dashboard using Selenium and verifies that:
1. MicroFrontEndTiming events appear in New Relic
2. All 4 microfrontends report telemetry
3. Required timing fields exist (timeToLoad, timeToRegister, timeAlive)
4. Source IDs match expected UUIDs

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable (defaults to 4182956)
- Frontend service running with microfrontends built
- Browser agent configured with api.register.enabled = true
- Chrome and chromedriver installed
"""

import os
import time
import pytest
import requests

from generate_mfe_traffic import generate_mfe_traffic_with_selenium

# Configuration
FRONTEND_URL = os.getenv("RELIBANK_URL", "http://localhost:3000")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")

# Microfrontend entity GUIDs
MFE_CONFIGS = {
    'AdBanner': '550e8400-e29b-41d4-a716-446655440000',
    'SpendingChart': '650e8400-e29b-41d4-a716-446655440001',
    'SpendingCategories': '750e8400-e29b-41d4-a716-446655440002',
    'AccountBalanceTrends': '850e8400-e29b-41d4-a716-446655440003'
}

# Skip all tests if New Relic credentials not provided
pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set"
)


def generate_dashboard_traffic():
    """
    Generate traffic to dashboard using Selenium to trigger microfrontend events.

    Uses real browser execution where:
    - JavaScript actually runs
    - MFEs actually load
    - Browser agent captures real telemetry
    - Actual .register() calls occur

    Waits for New Relic data ingestion after traffic generation.
    """
    print("\n" + "="*80)
    print("SETUP: Generating dashboard traffic with Selenium")
    print("="*80)

    print(f"Frontend URL: {FRONTEND_URL}")
    print("Using headless Chrome to generate real MFE events...")

    # Generate real browser traffic with Selenium
    generate_mfe_traffic_with_selenium(FRONTEND_URL)

    print("\n⏳ Waiting 90 seconds for New Relic ingestion...")
    print("   (MicroFrontEndTiming events may take longer than Transaction events)")
    print("="*80 + "\n")

    time.sleep(90)


def query_nrql(nrql_query):
    """
    Query New Relic using NRQL via NerdGraph GraphQL API.

    Args:
        nrql_query: NRQL query string to execute

    Returns:
        List of result objects from the query
    """
    url = "https://api.newrelic.com/graphql"
    headers = {
        "Content-Type": "application/json",
        "API-Key": NEW_RELIC_API_KEY
    }

    # Clean up NRQL query - remove extra whitespace and newlines
    cleaned_query = ' '.join(nrql_query.split())
    # Escape quotes for GraphQL
    escaped_query = cleaned_query.replace('"', '\\"')

    query = f"""
    {{
      actor {{
        account(id: {NEW_RELIC_ACCOUNT_ID}) {{
          nrql(query: "{escaped_query}") {{
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


@pytest.mark.slow
def test_microfrontend_timing_events_exist():
    """
    Verify MicroFrontEndTiming events appear in New Relic.

    This test confirms that at least one MicroFrontEndTiming event exists
    for the microfrontends we're tracking.
    """
    print("\n=== Test: MicroFrontEndTiming Events Exist ===")

    # Generate traffic first
    generate_dashboard_traffic()

    # Query for MicroFrontEndTiming events from any of our 4 MFEs
    # Note: Use source.id which contains our configured UUIDs, not entityGuid
    source_ids = "', '".join(MFE_CONFIGS.values())
    nrql = f"""
        SELECT count(*) FROM MicroFrontEndTiming
        WHERE source.id IN ('{source_ids}')
        SINCE 10 minutes ago
    """

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)
    count = results[0]["count"] if results else 0

    print(f"\n📊 MicroFrontEndTiming event count: {count}")

    assert count > 0, \
        f"Expected MicroFrontEndTiming events for microfrontends, found {count}. " \
        "Ensure browser agent has api.register.enabled = true and MFEs are calling .register()"

    print(f"✅ Found {count} MicroFrontEndTiming event(s)")


@pytest.mark.slow
def test_microfrontend_timing_fields():
    """
    Verify timeToLoad, timeToRegister, timeAlive fields exist.

    These fields are automatically added by the New Relic Browser agent's
    .register() API and are critical for microfrontend performance monitoring.
    """
    print("\n=== Test: MicroFrontEndTiming Fields ===")

    # Generate traffic first
    generate_dashboard_traffic()

    source_ids = "', '".join(MFE_CONFIGS.values())
    nrql = f"""
        SELECT timeToLoad, timeToRegister, timeAlive, source.id, entity.name
        FROM MicroFrontEndTiming
        WHERE source.id IN ('{source_ids}')
        SINCE 10 minutes ago LIMIT 100
    """

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)

    print(f"\n📊 Found {len(results)} MicroFrontEndTiming event(s)")

    assert len(results) > 0, \
        "No MicroFrontEndTiming events found. " \
        "Check that dashboard is accessible and MFEs are registering."

    # Verify each event has required fields
    missing_fields = []
    invalid_values = []

    for event in results:
        source_id = event.get('source.id', 'unknown')

        # Check for required fields
        required_fields = ['timeToLoad', 'timeToRegister', 'timeAlive', 'source.id']
        for field in required_fields:
            if field not in event:
                missing_fields.append(f"{field} missing in event with source.id={source_id}")

        # Verify timing values are non-negative numbers
        if 'timeToLoad' in event and event['timeToLoad'] < 0:
            invalid_values.append(f"timeToLoad={event['timeToLoad']} for source.id={source_id}")
        if 'timeToRegister' in event and event['timeToRegister'] < 0:
            invalid_values.append(f"timeToRegister={event['timeToRegister']} for source.id={source_id}")
        if 'timeAlive' in event and event['timeAlive'] < 0:
            invalid_values.append(f"timeAlive={event['timeAlive']} for source.id={source_id}")

    # Print sample event for debugging
    if results:
        print("\nSample event:")
        sample = results[0]
        print(f"  source.id: {sample.get('source.id', 'N/A')}")
        print(f"  entity.name: {sample.get('entity.name', 'N/A')}")
        print(f"  timeToLoad: {sample.get('timeToLoad', 'N/A')}ms")
        print(f"  timeToRegister: {sample.get('timeToRegister', 'N/A')}ms")
        print(f"  timeAlive: {sample.get('timeAlive', 'N/A')}ms")

    assert len(missing_fields) == 0, \
        f"Missing required fields in MicroFrontEndTiming events: {missing_fields}"

    assert len(invalid_values) == 0, \
        f"Invalid timing values in MicroFrontEndTiming events: {invalid_values}"

    print(f"✅ All {len(results)} event(s) have valid timing fields")


@pytest.mark.slow
def test_all_microfrontends_report_telemetry():
    """
    Verify all 4 microfrontends report telemetry.

    Checks that AdBanner, SpendingChart, SpendingCategories, and
    AccountBalanceTrends all generate MicroFrontEndTiming events.
    """
    print("\n=== Test: All Microfrontends Report Telemetry ===")

    # Generate traffic first
    generate_dashboard_traffic()

    reported_mfes = {}

    # Query each MFE individually
    for mfe_name, source_id in MFE_CONFIGS.items():
        nrql = f"""
            SELECT count(*) FROM MicroFrontEndTiming
            WHERE source.id = '{source_id}'
            SINCE 10 minutes ago
        """

        print(f"\nChecking {mfe_name} (source.id: {source_id})...")
        results = query_nrql(nrql)
        count = results[0]["count"] if results else 0
        reported_mfes[mfe_name] = count

        if count > 0:
            print(f"  ✓ {mfe_name}: {count} event(s)")
        else:
            print(f"  ✗ {mfe_name}: NO events")

    # Summary
    print("\n📊 Summary:")
    total_events = sum(reported_mfes.values())
    reporting_count = len([name for name, count in reported_mfes.items() if count > 0])
    print(f"   Total events: {total_events}")
    print(f"   Reporting MFEs: {reporting_count}/{len(MFE_CONFIGS)}")

    # Identify missing MFEs
    missing_mfes = [name for name, count in reported_mfes.items() if count == 0]

    if missing_mfes:
        print(f"\n⚠ Missing telemetry for: {', '.join(missing_mfes)}")
        print("\nPossible causes:")
        print("  - MFE script not loaded (check /public/microfrontends/)")
        print("  - Container element not found in DOM")
        print("  - .register() not called in MFE mount function")
        print("  - Browser agent api.register.enabled = false")

    assert len(missing_mfes) == 0, \
        f"Missing telemetry for microfrontends: {missing_mfes}. " \
        f"Only {reporting_count}/{len(MFE_CONFIGS)} MFEs reported events."

    print(f"\n✅ All {len(MFE_CONFIGS)} microfrontends reporting telemetry")


@pytest.mark.slow
def test_microfrontend_source_ids():
    """
    Verify source.id values match expected UUIDs.

    Ensures that the source.id field in MicroFrontEndTiming events matches
    the UUIDs configured in the microfrontend mount functions.
    """
    print("\n=== Test: Microfrontend Source IDs ===")

    # Generate traffic first
    generate_dashboard_traffic()

    # Query for unique source.id values
    nrql = """
        SELECT uniques(source.id) FROM MicroFrontEndTiming
        SINCE 10 minutes ago
    """

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)

    # Extract unique source IDs
    found_ids = []
    if results and len(results) > 0:
        for result in results:
            if 'members' in result:
                found_ids.extend(result['members'])
            elif 'uniques.source.id' in result:
                found_ids.extend(result['uniques.source.id'])

    # Also try direct query if uniques() format is different
    if not found_ids:
        nrql_fallback = """
            SELECT source.id FROM MicroFrontEndTiming
            SINCE 10 minutes ago LIMIT 1000
        """
        print("  Trying fallback query for source.id...")
        results_fallback = query_nrql(nrql_fallback)
        found_ids = list(set([r.get('source.id') for r in results_fallback if 'source.id' in r]))

    print(f"\n📊 Found source.id values:")
    for source_id in found_ids:
        matching_mfe = [name for name, expected_id in MFE_CONFIGS.items() if expected_id == source_id]
        if matching_mfe:
            print(f"  ✓ {source_id} ({matching_mfe[0]})")
        else:
            print(f"  ⚠ {source_id} (unknown MFE)")

    # Expected IDs
    expected_ids = set(MFE_CONFIGS.values())
    found_ids_set = set(found_ids)

    # Check for missing IDs
    missing_ids = expected_ids - found_ids_set
    unexpected_ids = found_ids_set - expected_ids

    if missing_ids:
        print(f"\n⚠ Missing expected source.id values:")
        for source_id in missing_ids:
            mfe_name = [name for name, sid in MFE_CONFIGS.items() if sid == source_id][0]
            print(f"  - {source_id} ({mfe_name})")

    if unexpected_ids:
        print(f"\n⚠ Unexpected source.id values found:")
        for source_id in unexpected_ids:
            print(f"  - {source_id}")

    assert len(missing_ids) == 0, \
        f"Missing source.id values: {missing_ids}. " \
        "Check that all MFEs are calling .register() with correct UUIDs."

    print(f"\n✅ All {len(expected_ids)} expected source.id values present")


if __name__ == "__main__":
    # Allow running tests directly
    import sys

    if not NEW_RELIC_API_KEY:
        print("❌ NEW_RELIC_USER_API_KEY environment variable not set")
        print("   Please set it to run microfrontend telemetry tests")
        sys.exit(1)

    print("🧪 Running Microfrontend Telemetry Tests")
    print(f"   Account ID: {NEW_RELIC_ACCOUNT_ID}")
    print(f"   Frontend URL: {FRONTEND_URL}")
    print(f"   Microfrontends: {', '.join(MFE_CONFIGS.keys())}")

    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=line"])

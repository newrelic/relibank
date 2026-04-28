"""
Test MFE timing events with browser interactions.

Generates traffic using Selenium with MFE interactions (button clicks, navigation)
and verifies that MicroFrontEndTiming events are captured with valid timing fields.

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable (defaults to 4182956)
- Frontend service running with microfrontends built
- Chrome and chromedriver installed
"""

import os
import time
import pytest

from generate_mfe_traffic import generate_mfe_traffic_with_selenium
from test_microfrontend_telemetry import query_nrql

FRONTEND_URL = os.getenv("RELIBANK_URL", "http://localhost:3000")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")

MFE_NAMES = {
    '550e8400-e29b-41d4-a716-446655440000': 'AdBanner',
    '650e8400-e29b-41d4-a716-446655440001': 'SpendingChart',
    '750e8400-e29b-41d4-a716-446655440002': 'SpendingCategories',
    '850e8400-e29b-41d4-a716-446655440003': 'AccountBalanceTrends',
}
MFE_SOURCE_IDS_LIST = list(MFE_NAMES.keys())
MFE_SOURCE_IDS = ", ".join(f"'{sid}'" for sid in MFE_SOURCE_IDS_LIST)

pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set"
)


def generate_traffic():
    """Generate MFE traffic with interactions and wait for New Relic ingestion."""
    print("\n" + "=" * 80)
    print("SETUP: Generating dashboard traffic with MFE interactions")
    print("=" * 80)
    print(f"Frontend URL: {FRONTEND_URL}")

    generate_mfe_traffic_with_selenium(FRONTEND_URL)

    print("\n⏳ Waiting 90 seconds for New Relic ingestion...")
    print("=" * 80 + "\n")
    time.sleep(90)


@pytest.mark.slow
def test_mfe_timing_events_exist():
    """Verify MicroFrontEndTiming events appear in New Relic after interaction traffic."""
    generate_traffic()

    nrql = f"""
        SELECT count(*) FROM MicroFrontEndTiming
        WHERE source.id IN ({MFE_SOURCE_IDS})
        FACET source.id
        SINCE 15 minutes ago
    """

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)

    counts_by_id = {r["source.id"]: r["count"] for r in results if "source.id" in r}
    print("MicroFrontEndTiming event counts by source.id:")
    for sid, count in counts_by_id.items():
        print(f"  {sid}: {count}  ({MFE_NAMES.get(sid, 'unknown')})")

    missing = [sid for sid in MFE_SOURCE_IDS_LIST if counts_by_id.get(sid, 0) == 0]

    assert len(missing) == 0, (
        f"Expected all MFEs to report MicroFrontEndTiming events after interaction traffic, "
        f"but {len(missing)} did not: {missing}. "
        "Ensure browser agent has api.register.enabled = true and MFEs are calling .register()"
    )

    print(f"✅ All {len(MFE_SOURCE_IDS_LIST)} MFEs reported MicroFrontEndTiming events")


@pytest.mark.slow
def test_mfe_timing_event_details():
    """Verify MicroFrontEndTiming events contain valid timing fields."""
    generate_traffic()

    nrql = f"""
        SELECT timeToLoad, timeToRegister, timeAlive, source.id, entity.name
        FROM MicroFrontEndTiming
        WHERE source.id IN ({MFE_SOURCE_IDS})
        SINCE 15 minutes ago LIMIT 10
    """

    print(f"Querying NRQL: {nrql}")
    results = query_nrql(nrql)

    assert len(results) > 0, (
        "No MicroFrontEndTiming events found. "
        "Check that dashboard is accessible and MFEs are registering."
    )

    for event in results:
        print(f"  - {event.get('entity.name')}: timeToRegister={event.get('timeToRegister')}ms")

    print(f"✅ Found {len(results)} MicroFrontEndTiming event(s) with details")

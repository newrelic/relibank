import os
import time
from generate_mfe_traffic import generate_mfe_traffic_with_selenium
from test_microfrontend_telemetry import query_nrql

# Get from environment variables
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")

if not NEW_RELIC_API_KEY:
    print("ERROR: NEW_RELIC_USER_API_KEY environment variable not set")
    print("Usage: export NEW_RELIC_USER_API_KEY='your-key' && python test_with_interactions.py")
    exit(1)

print("=" * 80)
print("Testing with MFE Interactions (matching goblin-swarm)")
print("=" * 80)

print("\n1. Generating traffic with MFE interactions...")
generate_mfe_traffic_with_selenium("http://localhost:3000")

print("\n2. Waiting 90 seconds for New Relic ingestion...")
time.sleep(90)

print("\n3. Querying for MicroFrontEndTiming events...")
nrql = """
    SELECT count(*) FROM MicroFrontEndTiming
    WHERE source.id IN ('550e8400-e29b-41d4-a716-446655440000', '650e8400-e29b-41d4-a716-446655440001', '750e8400-e29b-41d4-a716-446655440002', '850e8400-e29b-41d4-a716-446655440003')
    SINCE 15 minutes ago
"""

results = query_nrql(nrql)
count = results[0]["count"] if results else 0
print(f"\n📊 MicroFrontEndTiming events found: {count}")

if count > 0:
    print("\n✅ SUCCESS! Events are appearing with MFE interactions!")
    print("\nQuerying for details...")
    detail_nrql = """
        SELECT timeToLoad, timeToRegister, timeAlive, source.id, entity.name
        FROM MicroFrontEndTiming
        WHERE source.id IN ('550e8400-e29b-41d4-a716-446655440000', '650e8400-e29b-41d4-a716-446655440001', '750e8400-e29b-41d4-a716-446655440002', '850e8400-e29b-41d4-a716-446655440003')
        SINCE 15 minutes ago LIMIT 10
    """
    events = query_nrql(detail_nrql)
    for event in events:
        print(f"  - {event.get('entity.name')}: timeToRegister={event.get('timeToRegister')}ms")
else:
    print("\n⚠️ No events yet")
    print("Checking for any MicroFrontEndTiming events at all...")
    any_nrql = "SELECT count(*) FROM MicroFrontEndTiming SINCE 15 minutes ago"
    any_results = query_nrql(any_nrql)
    any_count = any_results[0]["count"] if any_results else 0
    print(f"Total MicroFrontEndTiming events (all sources): {any_count}")

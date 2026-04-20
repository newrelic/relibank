import os
import time
from generate_mfe_traffic import generate_mfe_traffic_with_selenium

FRONTEND_URL = os.getenv("RELIBANK_URL", "http://localhost:3000")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")

if not NEW_RELIC_API_KEY:
    print("ERROR: NEW_RELIC_USER_API_KEY environment variable not set")
    print("Usage: export NEW_RELIC_USER_API_KEY='your-key' && python test_mfe_single.py")
    exit(1)

from test_microfrontend_telemetry import query_nrql

print("Generating traffic...")
generate_mfe_traffic_with_selenium(FRONTEND_URL)

print("\nWaiting 180 seconds (3 minutes) for New Relic ingestion...")
time.sleep(180)

nrql = """
    SELECT count(*) FROM MicroFrontEndTiming
    WHERE source.id IN ('550e8400-e29b-41d4-a716-446655440000', '650e8400-e29b-41d4-a716-446655440001', '750e8400-e29b-41d4-a716-446655440002', '850e8400-e29b-41d4-a716-446655440003')
    SINCE 15 minutes ago
"""

print(f"\nQuerying New Relic...")
results = query_nrql(nrql)
count = results[0]["count"] if results else 0
print(f"MicroFrontEndTiming events found: {count}")

if count > 0:
    print("\n✅ SUCCESS! Events are appearing in New Relic!")
else:
    print("\n⚠️ No events yet - might need prod/staging environment")

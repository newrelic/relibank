"""
Kafka broker/cluster monitoring — post-deployment freshness tests.

Generates a single card-payment request to produce real Kafka traffic, then
waits for the collector scrape interval + New Relic ingestion, and verifies
that Kafka broker, cluster, and topic metrics are FRESH in New Relic (not
just present at some point in the last 24h -- stale historical data is what
masked the original outage, so these assert recency).

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable
- bill-pay-service running and otel-collector-kafka active
"""

import os
import time
import pytest
import requests
from pathlib import Path


def load_env_from_skaffold():
    """Load environment variables from skaffold.env if file exists (local development)."""
    skaffold_env = Path(__file__).parent.parent / "skaffold.env"
    if skaffold_env.exists():
        with open(skaffold_env) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val


load_env_from_skaffold()

NEW_RELIC_API_KEY    = os.getenv("NEW_RELIC_USER_API_KEY", "")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "")
BILL_PAY_SERVICE_URL  = os.getenv("BILL_PAY_SERVICE_URL", "http://localhost:5000")
NERDGRAPH_URL        = "https://api.newrelic.com/graphql"
TARGET_COLOR         = os.getenv("TARGET_COLOR", "").strip()

FRESHNESS_WINDOW = "5 minutes ago"

# otel-collector-kafka's KAFKA_CLUSTER_NAME is color-suffixed in every Terraform-deployed
# env (sandbox/staging/prod) precisely so blue and green don't collide into one entity --
# killing one color's collector is invisible in NR as long as the other color's is still
# reporting under the same identity. Legacy k8s/base (events, local dev) has no color
# concept and keeps the bare "relibank-kafka" name, so fall back to that when TARGET_COLOR
# isn't set rather than filtering on a cluster name that would never match there.
KAFKA_CLUSTER_NAME = f"relibank-kafka-{TARGET_COLOR}" if TARGET_COLOR else "relibank-kafka"

pytestmark = [
    pytest.mark.skipif(
        not NEW_RELIC_API_KEY,
        reason="NEW_RELIC_USER_API_KEY environment variable not set",
    ),
    # generate_kafka_traffic sleeps 90s after its POST before any assertion runs;
    # override the workflow's blanket --timeout=300 so pytest-timeout doesn't kill mid-fixture.
    pytest.mark.timeout(300),
]


def query_nerdgraph(nrql: str) -> list:
    """Execute a NRQL query via NerdGraph and return the results list."""
    query = f"""
    {{
      actor {{
        account(id: {NEW_RELIC_ACCOUNT_ID}) {{
          nrql(query: "{nrql}") {{
            results
          }}
        }}
      }}
    }}
    """
    resp = requests.post(
        NERDGRAPH_URL,
        json={"query": query},
        headers={"API-Key": NEW_RELIC_API_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"NerdGraph errors: {data['errors']}")
    return data["data"]["actor"]["account"]["nrql"]["results"]


_load_generated = False


@pytest.fixture(scope="module", autouse=True)
def generate_kafka_traffic():
    """
    Produces one real Kafka message so the kafka.prod.msg.count check below doesn't
    depend on ambient scenario/load traffic -- confirmed live against staging that
    background traffic does NOT reliably touch the real payment topics there (only
    the internal __consumer_offsets topic showed recent activity), even though
    sandbox/prod did. A card payment is the cheapest, most idempotent producer path:
    Stripe test-mode card, no real account-balance mutation, and it publishes to the
    `card_payments` topic on success (bill_pay_service.py's process_card_payment).

    Sleep budget after the POST: no multi-phase load needed here (unlike the MSSQL
    lock-contention fixture) -- 90s covers the collector's 30s JMX scrape interval
    plus New Relic ingestion lag.
    """
    global _load_generated
    if _load_generated:
        return
    _load_generated = True

    payload = {
        "billId": f"CARD-{int(time.time())}",
        "amount": 10.00,
        "currency": "usd",
        "paymentMethodId": "pm_card_visa",  # Stripe test card
        "saveCard": False,
        "payee": "Electric Company",
        "accountId": "acc-test-standard",
    }
    try:
        requests.post(
            f"{BILL_PAY_SERVICE_URL}/bill-pay-service/card-payment",
            json=payload,
            timeout=30,
        )
    except Exception:
        pass

    time.sleep(90)


def test_kafka_broker_uptime_is_fresh():
    """Verifies kafka.broker.uptime (entity.type = KAFKABROKER) has a recent data point.

    This is the exact signal that went dark for ~18h in the RCA this test guards
    against: otel-collector-kafka's JMX connection to the broker doesn't survive a
    broker pod replacement and never reconnects on its own.
    """
    results = query_nerdgraph(
        f"SELECT count(*) FROM Metric WHERE entity.type = 'KAFKABROKER' "
        f"AND kafka.cluster.name = '{KAFKA_CLUSTER_NAME}' "
        f"AND metricName = 'kafka.broker.uptime' SINCE {FRESHNESS_WINDOW}"
    )
    assert results, "No results from NRQL query"
    assert results[0].get("count", 0) > 0, (
        f"kafka.broker.uptime has no data point in the last {FRESHNESS_WINDOW} for "
        f"cluster '{KAFKA_CLUSTER_NAME}' -- otel-collector-kafka's JMX connection to "
        "the broker may be stale/dead."
    )


def test_kafka_cluster_brokers_is_fresh():
    """Verifies kafka.brokers (entity.type = KAFKACLUSTER) has a recent data point.

    Sourced from the admin-client-based kafkametrics receiver, which auto-reconnects
    -- expected to stay healthy independently of the JMX scraper above.
    """
    results = query_nerdgraph(
        f"SELECT count(*) FROM Metric WHERE entity.type = 'KAFKACLUSTER' "
        f"AND kafka.cluster.name = '{KAFKA_CLUSTER_NAME}' "
        f"AND metricName = 'kafka.brokers' SINCE {FRESHNESS_WINDOW}"
    )
    assert results, "No results from NRQL query"
    assert results[0].get("count", 0) > 0, (
        f"kafka.brokers has no data point in the last {FRESHNESS_WINDOW} for cluster "
        f"'{KAFKA_CLUSTER_NAME}'."
    )


def test_kafka_topic_msg_count_is_fresh():
    """Verifies kafka.prod.msg.count (entity.type = KAFKATOPIC) has a recent data point
    for the `card_payments` topic the fixture above just produced to.

    Despite being topic/app-shaped, this metric is actually scraped via the SAME JMX
    bean (BrokerTopicMetrics,MessagesInPerSec) as kafka.broker.uptime -- so it shares
    that scraper's stale-connection fate, not independent "app instrumentation" as it
    might first appear. Scoped to one topic (rather than faceted across all of them)
    so this check doesn't depend on ambient traffic to the other topics.
    """
    results = query_nerdgraph(
        f"SELECT count(*) FROM Metric WHERE entity.type = 'KAFKATOPIC' "
        f"AND kafka.cluster.name = '{KAFKA_CLUSTER_NAME}' "
        f"AND metricName = 'kafka.prod.msg.count' AND topic = 'card_payments' "
        f"SINCE {FRESHNESS_WINDOW}"
    )
    assert results, "No results from NRQL query"
    assert results[0].get("count", 0) > 0, (
        f"kafka.prod.msg.count for topic 'card_payments' on cluster "
        f"'{KAFKA_CLUSTER_NAME}' has no data point in the last {FRESHNESS_WINDOW}."
    )

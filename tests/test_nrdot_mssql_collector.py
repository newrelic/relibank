import os
import time
import threading
import requests
import pytest
from pathlib import Path


def load_env_from_skaffold():
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

NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY", "")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "")
TRANSACTION_SERVICE = os.getenv("TRANSACTION_SERVICE", "http://localhost:5001")
NERDGRAPH_URL = "https://api.newrelic.com/graphql"

pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set",
)


def query_nerdgraph(nrql: str) -> list:
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
def generate_mssql_load():
    """
    Sends sustained POST /adjust-amount requests for ~120 s, then waits
    90 s for the collector scrape interval (60 s) + NR ingestion.
    Runs once per test module.
    """
    global _load_generated
    if _load_generated:
        return
    _load_generated = True

    stop_event = threading.Event()

    def _send_requests():
        url = f"{TRANSACTION_SERVICE}/transaction-service/adjust-amount"
        i = 0
        while not stop_event.is_set():
            try:
                requests.post(
                    url,
                    json={"bill_id": f"NRDOT-TEST-{i:05d}", "adjustment_percent": 0.01},
                    timeout=5,
                )
            except Exception:
                pass
            i += 1
            time.sleep(0.5)  # ~2 req/s = ~240 reqs over 120 s

    t = threading.Thread(target=_send_requests, daemon=True)
    t.start()
    time.sleep(120)
    stop_event.set()
    t.join(timeout=5)

    # Wait for collector scrape (60 s) + NR ingestion buffer (30 s)
    time.sleep(90)


def test_lock_contention_metrics():
    """Verifies lock waits, timeouts, and deadlock rate metrics land in NR."""
    results = query_nerdgraph(
        "SELECT rate(sum(sqlserver.stats.lock_waits_per_sec), 1 minute) AS 'lockWaitsPerMin', "
        "rate(sum(sqlserver.instance.lock_timeouts_rate), 1 minute) AS 'lockTimeoutsPerMin', "
        "rate(sum(sqlserver.stats.deadlocks_per_sec), 1 minute) AS 'deadlocksPerMin' "
        "FROM Metric "
        "WHERE instrumentation.provider = 'opentelemetry' "
        "SINCE 10 minutes ago"
    )
    assert results, "No lock contention metrics found in New Relic"
    row = results[0]
    assert any(v is not None for v in row.values()), (
        f"All lock contention values are null: {row}"
    )


def test_connection_and_throughput_metrics():
    """Verifies active connections and transactions-per-second metrics land in NR."""
    results = query_nerdgraph(
        "SELECT latest(sqlserver.stats.connections) AS 'connections', "
        "rate(sum(sqlserver.instance.transactions_per_sec), 1 minute) AS 'tpsPerMin' "
        "FROM Metric "
        "WHERE instrumentation.provider = 'opentelemetry' "
        "SINCE 10 minutes ago"
    )
    assert results, "No connection/throughput metrics found in New Relic"
    row = results[0]
    assert any(v is not None for v in row.values()), (
        f"All connection/TPS values are null: {row}"
    )


def test_buffer_pool_metrics():
    """Verifies buffer pool hit % and page life expectancy metrics land in NR."""
    results = query_nerdgraph(
        "SELECT latest(sqlserver.instance.buffer_pool_hit_percent) AS 'bufferPoolHitPct', "
        "latest(sqlserver.bufferpool.page_life_expectancy_ms) AS 'pageLifeExpMs' "
        "FROM Metric "
        "WHERE instrumentation.provider = 'opentelemetry' "
        "SINCE 10 minutes ago"
    )
    assert results, "No buffer pool metrics found in New Relic"
    row = results[0]
    assert any(v is not None for v in row.values()), (
        f"All buffer pool values are null: {row}"
    )


def test_sql_compilation_metrics():
    """Verifies SQL compilation and recompilation rate metrics land in NR."""
    results = query_nerdgraph(
        "SELECT rate(sum(sqlserver.stats.sql_compilations_per_sec), 1 minute) AS 'compilationsPerMin', "
        "rate(sum(sqlserver.stats.sql_recompilations_per_sec), 1 minute) AS 'recompilationsPerMin', "
        "rate(sum(sqlserver.instance.forced_parameterizations_per_sec), 1 minute) AS 'forcedParamsPerMin' "
        "FROM Metric "
        "WHERE instrumentation.provider = 'opentelemetry' "
        "SINCE 10 minutes ago"
    )
    assert results, "No SQL compilation metrics found in New Relic"
    row = results[0]
    assert any(v is not None for v in row.values()), (
        f"All compilation values are null: {row}"
    )


def test_wait_stats_metrics():
    """Verifies sqlserver wait stats metrics land in NR."""
    results = query_nerdgraph(
        "SELECT rate(sum(sqlserver.wait_stats.wait_time_ms), 1 minute) AS 'totalWaitTimePerMin' "
        "FROM Metric "
        "WHERE instrumentation.provider = 'opentelemetry' "
        "AND metricName LIKE 'sqlserver.wait_stats.%' "
        "SINCE 10 minutes ago"
    )
    assert results, "No wait stats metrics found in New Relic"
    row = results[0]
    assert any(v is not None for v in row.values()), (
        f"All wait stats values are null: {row}"
    )

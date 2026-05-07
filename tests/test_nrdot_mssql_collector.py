"""
NRDOT MSSQL Collector — verification tests.

Generates sustained POST /adjust-amount traffic to produce real MSSQL activity,
then waits for the collector scrape interval + New Relic ingestion, and verifies
that MSSQL metrics landed in New Relic via NRQL queries.

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable
- Transaction service running and NRDOT collector active
"""

import os
import time
import threading
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
TRANSACTION_SERVICE  = os.getenv("TRANSACTION_SERVICE", "http://localhost:5001")
NERDGRAPH_URL        = "https://api.newrelic.com/graphql"

pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set",
)


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
def generate_mssql_load():
    """
    Three-phase load to ensure both completed slow-query executions and real lock
    contention reach New Relic before the NRQL assertions run.

    Phase 1 (0–30s):   Slow queries + adjust-amount run freely, building Query
                       Store history with real elapsed times.
    Phase 2 (30–330s): Blocking session holds UPDLOCK for 300s. Subsequent
                       adjust-amount calls contend → lock-wait events visible in
                       sys.dm_exec_requests. 300s >> NR ingest lag (~90s), so
                       blocked queries are observable in the Active Queries UI
                       well before the blocker releases.
                       Slow queries continue throughout for execution plan data.
    Phase 3 (120s):    NRDOT scrape cycle (60s) + NR ingestion buffer (60s).
    """
    global _load_generated
    if _load_generated:
        return
    _load_generated = True

    stop_event  = threading.Event()
    query_types = ["spending_velocity", "merchant_risk", "transaction_patterns", "account_velocity", "flagged_analysis"]

    def _send_requests():
        adjust_url = f"{TRANSACTION_SERVICE}/transaction-service/adjust-amount/BILL-1701"
        slow_url   = f"{TRANSACTION_SERVICE}/transaction-service/slow-query"
        i = 0
        while not stop_event.is_set():
            try:
                if i % 3 == 0:
                    qt = query_types[i % len(query_types)]
                    requests.get(f"{slow_url}?query_type={qt}&delay_seconds=6", timeout=60)
                else:
                    requests.post(f"{adjust_url}?adjustment=1.00", timeout=10)
            except Exception:
                pass
            i += 1
            time.sleep(0.5)  # ~2 req/s

    # Phase 1: slow queries complete freely → builds Query Store history.
    t = threading.Thread(target=_send_requests, daemon=True)
    t.start()
    time.sleep(30)

    # Phase 2: blocking session holds for 300s so that NR ingest (~90s lag)
    # has plenty of time to surface blocked queries in the Active Queries UI
    # while the blocker is still running.
    def _blocking_session():
        try:
            requests.get(
                f"{TRANSACTION_SERVICE}/transaction-service/blocking?delay_seconds=300",
                timeout=310,
            )
        except Exception:
            pass

    blocker = threading.Thread(target=_blocking_session, daemon=True)
    blocker.start()
    time.sleep(300)

    stop_event.set()
    t.join(timeout=15)
    blocker.join(timeout=10)

    # Phase 3: NRDOT scrape cycle (60s) + NR ingestion buffer (60s).
    time.sleep(120)


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

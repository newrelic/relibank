"""
nri-postgresql (classic on-host integration) — verification tests.

Generates light GET traffic against accounts-service to produce real Postgres
activity, then waits for the integration's collection interval + New Relic
ingestion, and verifies that Postgres metrics/query data landed in New Relic
via NRQL queries.

Unlike the MSSQL collector (an OTel/NRDOT pipeline reporting `Metric` events
with instrumentation.provider='opentelemetry'), nri-postgresql is the classic
on-host integration and reports its own native event types directly
(PostgresqlDatabaseSample, PostgresSlowQueries, PostgresIndividualQueries) —
no Metric/OTel filter needed.

PostgresWaitEvents is deliberately NOT hard-asserted here: a wait event only
gets sampled when a backend is actually waiting on something (lock, IO, etc.)
at the exact moment pg_wait_sampling snapshots it — inherently timing/
contention-dependent, not something a short, non-adversarial load window
reliably produces. The other three event types are strong indirect proof the
extension setup is correct anyway: nri-postgresql only emits PostgresSlowQueries/
PostgresIndividualQueries at all if pg_stat_statements/pg_stat_monitor are
present and being read successfully.

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable
- accounts-service running and nri-postgresql integration active
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
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE_URL", "http://localhost:5000")
NERDGRAPH_URL        = "https://api.newrelic.com/graphql"

pytestmark = [
    pytest.mark.skipif(
        not NEW_RELIC_API_KEY,
        reason="NEW_RELIC_USER_API_KEY environment variable not set",
    ),
    # generate_postgres_load sleeps 60s+90s before any assertion runs; override the
    # workflow's blanket --timeout=300 so pytest-timeout doesn't kill mid-fixture.
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
def generate_postgres_load():
    """
    Light, steady GET traffic against accounts-service to ensure Postgres query
    activity reaches New Relic before the NRQL assertions run.

    Unlike the MSSQL collector test, no deliberate lock-contention/blocking scenario
    is needed here — nri-postgresql's query-monitoring threshold is low enough that
    normal traffic alone reliably populates slow-query/individual-query data (confirmed
    empirically: ambient traffic alone produced hundreds of rows within ~10-20 minutes).

    Phase 1 (0-60s):  steady GET /accounts-service/accounts/{email} traffic.
    Phase 2 (60-150s): collection interval (15s) + NR ingestion buffer.
    """
    global _load_generated
    if _load_generated:
        return
    _load_generated = True

    stop_event = threading.Event()

    def _send_requests():
        accounts_url = f"{ACCOUNTS_SERVICE_URL}/accounts-service/accounts/alice.j@relibank.com"
        while not stop_event.is_set():
            try:
                requests.get(accounts_url, timeout=10)
            except Exception:
                pass
            time.sleep(0.5)  # ~2 req/s

    t = threading.Thread(target=_send_requests, daemon=True)
    t.start()
    time.sleep(60)

    stop_event.set()
    t.join(timeout=15)

    # Collection interval (15s) + NR ingestion buffer.
    time.sleep(90)


def test_database_sample_metrics():
    """Verifies basic PostgresqlDatabaseSample instance metrics land in NR."""
    results = query_nerdgraph(
        "SELECT count(*) FROM PostgresqlDatabaseSample SINCE 10 minutes ago"
    )
    assert results, "No PostgresqlDatabaseSample results returned from NRQL"
    assert results[0].get("count", 0) > 0, (
        f"No PostgresqlDatabaseSample events found in New Relic: {results[0]}"
    )


def test_slow_queries():
    """Verifies PostgresSlowQueries (query-level metrics) land in NR."""
    results = query_nerdgraph(
        "SELECT count(*) FROM PostgresSlowQueries SINCE 10 minutes ago"
    )
    assert results, "No PostgresSlowQueries results returned from NRQL"
    assert results[0].get("count", 0) > 0, (
        f"No PostgresSlowQueries events found in New Relic: {results[0]}"
    )


def test_individual_queries():
    """Verifies PostgresIndividualQueries (query detail/execution plan data) land in NR."""
    results = query_nerdgraph(
        "SELECT count(*) FROM PostgresIndividualQueries SINCE 10 minutes ago"
    )
    assert results, "No PostgresIndividualQueries results returned from NRQL"
    assert results[0].get("count", 0) > 0, (
        f"No PostgresIndividualQueries events found in New Relic: {results[0]}"
    )


def test_wait_events():
    """
    Logs whether PostgresWaitEvents (wait-time analysis) has landed in NR — informational
    only, not a hard requirement. A real wait event needs a backend to actually be waiting
    on something (lock, IO, etc.) at the exact moment pg_wait_sampling snapshots it, which
    a short, non-adversarial load window can't reliably force. Absence here doesn't mean
    the integration is broken — see test_slow_queries/test_individual_queries for the
    deterministic proof that pg_stat_statements/pg_stat_monitor are active and being read.
    """
    results = query_nerdgraph(
        "SELECT count(*) FROM PostgresWaitEvents SINCE 10 minutes ago"
    )
    count = results[0].get("count", 0) if results else 0
    if count > 0:
        print(f"PostgresWaitEvents: {count} events found in the last 10 minutes.")
    else:
        print(
            "PostgresWaitEvents: no events in the last 10 minutes (expected under light, "
            "non-contentious load — not a failure)."
        )

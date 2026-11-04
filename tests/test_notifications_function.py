"""
Notifications Azure Function APM instrumentation — verification tests.

Unlike the MSSQL collector tests, no synthetic load is generated here — base-load's
continuous demo traffic already invokes notify_user_trigger regularly, so these just
poll NRQL directly for the NR Python agent's APM entity, transactions, and distributed
tracing spans.

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable
- APP_NAME environment variable (e.g. "ReliBank (Sandbox)")
"""

import os
from pathlib import Path

import pytest
import requests


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

NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY", "")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "")
APP_NAME = os.getenv("APP_NAME", "")
NERDGRAPH_URL = "https://api.newrelic.com/graphql"
FUNCTION_APP_NAME = f"{APP_NAME} - Notifications Function"

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


def test_apm_entity_reporting():
    """notify_user_trigger's NR Python agent is producing real transactions, not just a
    registered-but-empty APM entity."""
    results = query_nerdgraph(
        "SELECT count(*) AS c FROM Transaction "
        f"WHERE appName = '{FUNCTION_APP_NAME}' "
        "AND name = 'WebTransaction/AzureFunction/notify_user' "
        "SINCE 10 minutes ago"
    )
    assert results, "No Transaction results returned"
    count = results[0].get("c") or 0
    assert count > 0, f"No notify_user transactions found for '{FUNCTION_APP_NAME}' in last 10 minutes"


def test_transaction_duration_and_error_state():
    """Transactions carry real duration and error/success state, not just a bare count."""
    results = query_nerdgraph(
        f"SELECT duration, error FROM Transaction WHERE appName = '{FUNCTION_APP_NAME}' SINCE 10 minutes ago LIMIT 5"
    )
    assert results, f"No transactions found for '{FUNCTION_APP_NAME}' in last 10 minutes"
    for row in results:
        assert row.get("duration") is not None, f"Transaction missing duration: {row}"
        assert "error" in row, f"Transaction missing error field: {row}"


def test_distributed_tracing():
    """Spans link into a real distributed trace (trace.id populated), not standalone spans."""
    results = query_nerdgraph(
        "SELECT count(*) AS c FROM Span "
        f"WHERE appName = '{FUNCTION_APP_NAME}' "
        "AND trace.id IS NOT NULL "
        "SINCE 10 minutes ago"
    )
    assert results, "No Span results returned"
    count = results[0].get("c") or 0
    assert count > 0, f"No spans with a populated trace.id found for '{FUNCTION_APP_NAME}'"

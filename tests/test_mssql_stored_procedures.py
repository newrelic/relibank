"""
MSSQL stored procedures — verification tests (NR-635348).

Unlike an earlier version of this file, no load is generated here — scheduler_service's
poll loop now calls all 3 procedures on its own cadence (sp_ProcessDueRecurringPayments
every minute, sp_CalculateSpendingVelocity and sp_RebuildAccountLedgerBalance every 5
minutes), so these just poll NRQL directly for recent activity.

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable
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
NERDGRAPH_URL = "https://api.newrelic.com/graphql"

STORED_PROCEDURES = [
    "[dbo].[sp_CalculateSpendingVelocity]",
    "[dbo].[sp_RebuildAccountLedgerBalance]",
    "[dbo].[sp_ProcessDueRecurringPayments]",
]

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


@pytest.mark.parametrize("procedure_name", STORED_PROCEDURES)
def test_stored_procedure_visible_in_top_procedure(procedure_name):
    """Each stored procedure appears as a named object in NR's per-procedure QPM rollup,
    not just ad-hoc SQL text. 10-minute window comfortably covers the slowest (5-minute)
    poll cadence."""
    results = query_nerdgraph(
        "SELECT count(*) AS c FROM DbServerTopProcedure "
        f"WHERE db.namespace = 'RelibankDB' AND sqlserver.procedure_name = '{procedure_name}' "
        "SINCE 10 minutes ago"
    )
    assert results, f"No DbServerTopProcedure results returned for {procedure_name}"
    count = results[0].get("c") or 0
    assert count > 0, f"{procedure_name} not found in DbServerTopProcedure in the last 10 minutes"


def test_execution_plan_data_present():
    """Execution-plan collection (DbServerQueryPlan) is actually populated for RelibankDB,
    not just registered-but-empty."""
    results = query_nerdgraph(
        "SELECT count(*) AS c FROM DbServerQueryPlan WHERE db.namespace = 'RelibankDB' "
        "SINCE 10 minutes ago"
    )
    assert results, "No DbServerQueryPlan results returned"
    count = results[0].get("c") or 0
    assert count > 0, "No execution plans captured for RelibankDB in the last 10 minutes"

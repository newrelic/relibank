"""
eBPF DNS error monitoring -- post-deployment regression guard.

Verifies the eBPF network agent is reporting and that DNS lookup errors stay at the
baseline expected after pods run with `ndots: 2` (terraform/aks/app_module/main.tf).
Mirrors the Platform alert conditions in terraform/aks/newrelic/nr_alerts.tf:
platform_network_agent_freshness, platform_dns_unexpected_errors and
platform_dns_nxdomain_regression.

The NXDOMAIN check is only meaningful once the ndots change is live in the target
environment. Before that, collector.newrelic.com search-path lookups sit far above
the threshold (~5,650/hour per cluster).

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable
- K8S_CLUSTER_NAME environment variable (optional, e.g. relibank-sandbox) to scope the
  queries to one cluster
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
K8S_CLUSTER_NAME = os.getenv("K8S_CLUSTER_NAME", "").strip()

FRESHNESS_WINDOW = "5 minutes"
ERROR_WINDOW = "30 minutes"

# Same rate as platform_dns_nxdomain_regression in nr_alerts.tf: 500 per 30 minutes = 1,000/hour.
NXDOMAIN_MAX_PER_30_MIN = 500

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


def where(*conditions: str) -> str:
    """Build a WHERE clause from conditions, adding the cluster scope when configured."""
    clauses = list(conditions)
    if K8S_CLUSTER_NAME:
        clauses.append(f"k8s.cluster.name = '{K8S_CLUSTER_NAME}'")
    return f"WHERE {' AND '.join(clauses)}" if clauses else ""


def scalar(nrql: str) -> float:
    """Run a single-value NRQL query and return that value (0 when empty)."""
    results = query_nerdgraph(nrql)
    assert results, "No results from NRQL query"
    return next(iter(results[0].values())) or 0


def test_ebpf_agent_is_reporting():
    """Verifies ebpf.tcp.connection.open has a recent data point.

    Same signal as platform_network_agent_freshness. The DNS metric can't be used for
    this: it may be empty when lookups are healthy.
    """
    count = scalar(f"SELECT count(ebpf.tcp.connection.open) FROM Metric {where()} SINCE {FRESHNESS_WINDOW} ago")
    scope = f" for cluster {K8S_CLUSTER_NAME}" if K8S_CLUSTER_NAME else ""
    assert count > 0, (
        f"ebpf.tcp.connection.open has no data point in the last {FRESHNESS_WINDOW}{scope} "
        "-- the eBPF agent may be missing or down."
    )


def test_no_unexpected_dns_errors():
    """Verifies there are no DNS errors other than NXDOMAIN (timeouts, SERVFAIL, refused).

    Same query as platform_dns_unexpected_errors; the baseline is 0.
    """
    clause = where("error.type IS NOT NULL", "error.type != 'NXDOMAIN'")
    count = scalar(f"SELECT count(dns.lookup.duration) FROM Metric {clause} SINCE {ERROR_WINDOW} ago")
    assert count == 0, f"{count} non-NXDOMAIN DNS errors in the last {ERROR_WINDOW}"


def test_collector_nxdomain_rate_is_below_threshold():
    """Regression guard for the ndots change: collector.newrelic.com NXDOMAIN answers.

    With the default ndots:5, every collector lookup first tries each cluster search suffix
    and gets NXDOMAIN. With ndots:2 the host is resolved as-is, so these should be near 0.
    """
    clause = where("error.type = 'NXDOMAIN'", "dns.question.name LIKE 'collector.newrelic.com%'")
    count = scalar(f"SELECT count(dns.lookup.duration) FROM Metric {clause} SINCE {ERROR_WINDOW} ago")
    assert count < NXDOMAIN_MAX_PER_30_MIN, (
        f"{count} collector.newrelic.com NXDOMAIN answers in the last {ERROR_WINDOW} "
        f"(limit {NXDOMAIN_MAX_PER_30_MIN}) -- pods may still be resolving with ndots:5."
    )

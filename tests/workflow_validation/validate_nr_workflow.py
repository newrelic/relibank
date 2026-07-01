"""
Post-apply validation for the ReliBank NR workflow.

Confirms two things after `relibank-newrelic.yml` runs `terraform apply`:

  1. The entities created by the `newrelic/newrelic` provider are present in NR
     (queryable from the API user's perspective). One test per entity type.
  2. The cluster-side helm releases installed by the same apply (`nri-bundle`,
     `nr-ebpf-agent`) are actually reporting telemetry — K8sClusterSample for
     the cluster, K8sPodSample for the `newrelic` namespace.

Modelled on demogorgon's test-scripts/nrql-data-validation.py: pytest file,
NerdGraph helper, env-var precondition, hard assertions. The workflow job uses
`continue-on-error: true` on the pytest step + a follow-up check step so per-
test failures stay visible in the report but the overall job still fails.

Run by `.github/workflows/relibank-newrelic.yml` (job `relibank-newrelic-validate`).
"""

import os

import pytest
import requests

API_KEY = os.environ.get("NR_USER_API_KEY")
ACCOUNT_ID = os.environ.get("NR_ACCOUNT_ID")
APP_NAME = os.environ.get("APP_NAME")
AKS_CLUSTER_NAME = os.environ.get("AKS_CLUSTER_NAME")

NERDGRAPH_ENDPOINT = "https://api.newrelic.com/graphql"

if not API_KEY:
    pytest.skip("NR_USER_API_KEY not set", allow_module_level=True)
if not ACCOUNT_ID:
    pytest.skip("NR_ACCOUNT_ID not set", allow_module_level=True)
if not APP_NAME:
    pytest.skip("APP_NAME not set", allow_module_level=True)
if not AKS_CLUSTER_NAME:
    pytest.skip("AKS_CLUSTER_NAME not set", allow_module_level=True)


def query_nerdgraph(graphql):
    response = requests.post(
        NERDGRAPH_ENDPOINT,
        headers={"API-Key": API_KEY, "Content-Type": "application/json"},
        json={"query": graphql},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise AssertionError(f"GraphQL errors: {data['errors']}")
    return data


def assert_entity_exists(name, entity_type):
    """Query NerdGraph entitySearch for `name` + `type`, assert at least one match."""
    graphql = f"""
    {{
      actor {{
        entitySearch(query: "name = '{name}' AND type = '{entity_type}'") {{
          results {{
            entities {{ guid name type }}
          }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    entities = (
        data.get("data", {})
        .get("actor", {})
        .get("entitySearch", {})
        .get("results", {})
        .get("entities", [])
    )
    matches = [e for e in entities if e.get("name") == name]
    assert matches, f"No {entity_type} entity found with name '{name}'"
    print(f"  OK {entity_type}: '{name}' (guid={matches[0]['guid']})")


def run_nrql(nrql):
    graphql = f"""
    {{
      actor {{
        account(id: {ACCOUNT_ID}) {{
          nrql(query: "{nrql}") {{ results }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    return (
        data.get("data", {})
        .get("actor", {})
        .get("account", {})
        .get("nrql", {})
        .get("results", [])
    )


# ---------------------------------------------------------------------------
# Group A: entity existence
# ---------------------------------------------------------------------------

def test_dashboard_entity_exists():
    """`newrelic_one_dashboard_json.placeholder` — Dashboard, queried via entitySearch."""
    assert_entity_exists(f"{APP_NAME} - Placeholder Dashboard", "DASHBOARD")


def test_workload_entity_exists():
    """`newrelic_workload.placeholder` — Workload, queried via entitySearch."""
    assert_entity_exists(f"{APP_NAME} - Placeholder Workload", "WORKLOAD")


def test_synthetics_ping_monitor_exists():
    """`newrelic_synthetics_monitor.placeholder_ping` — Monitor, queried via entitySearch."""
    assert_entity_exists(f"{APP_NAME} - Placeholder Ping", "MONITOR")


def test_synthetics_script_monitor_exists():
    """`newrelic_synthetics_script_monitor.placeholder_script` — Monitor, queried via entitySearch."""
    assert_entity_exists(f"{APP_NAME} - Placeholder Script Monitor", "MONITOR")


def test_alert_policy_exists():
    """`newrelic_alert_policy.placeholder` — queried via alerts.policiesSearch."""
    name = f"{APP_NAME} - Placeholder Policy"
    graphql = f"""
    {{
      actor {{
        account(id: {ACCOUNT_ID}) {{
          alerts {{
            policiesSearch(searchCriteria: {{ name: "{name}" }}) {{
              policies {{ id name }}
            }}
          }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    policies = (
        data.get("data", {})
        .get("actor", {})
        .get("account", {})
        .get("alerts", {})
        .get("policiesSearch", {})
        .get("policies", [])
    )
    matches = [p for p in policies if p.get("name") == name]
    assert matches, f"No alert policy found with name '{name}'"
    print(f"  OK alert policy: '{name}' (id={matches[0]['id']})")


def test_nrql_alert_condition_exists():
    """`newrelic_nrql_alert_condition.placeholder_support_service_error_rate` — queried via alerts.nrqlConditionsSearch."""
    name = f"{APP_NAME} - Placeholder Support Service Error Rate"
    graphql = f"""
    {{
      actor {{
        account(id: {ACCOUNT_ID}) {{
          alerts {{
            nrqlConditionsSearch(searchCriteria: {{ name: "{name}" }}) {{
              nrqlConditions {{ id name }}
            }}
          }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    conditions = (
        data.get("data", {})
        .get("actor", {})
        .get("account", {})
        .get("alerts", {})
        .get("nrqlConditionsSearch", {})
        .get("nrqlConditions", [])
    )
    matches = [c for c in conditions if c.get("name") == name]
    assert matches, f"No NRQL alert condition found with name '{name}'"
    print(f"  OK NRQL condition: '{name}' (id={matches[0]['id']})")


def test_notification_destination_exists():
    """`newrelic_notification_destination.placeholder_email` — queried via aiNotifications.destinations."""
    name = f"{APP_NAME} - Placeholder Email Destination"
    graphql = f"""
    {{
      actor {{
        account(id: {ACCOUNT_ID}) {{
          aiNotifications {{
            destinations(filters: {{ name: "{name}" }}) {{
              entities {{ id name }}
            }}
          }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    entities = (
        data.get("data", {})
        .get("actor", {})
        .get("account", {})
        .get("aiNotifications", {})
        .get("destinations", {})
        .get("entities", [])
    )
    matches = [e for e in entities if e.get("name") == name]
    assert matches, f"No notification destination found with name '{name}'"
    print(f"  OK destination: '{name}' (id={matches[0]['id']})")


def test_notification_channel_exists():
    """`newrelic_notification_channel.placeholder_email_template` — queried via aiNotifications.channels."""
    name = f"{APP_NAME} - Placeholder Email Template"
    graphql = f"""
    {{
      actor {{
        account(id: {ACCOUNT_ID}) {{
          aiNotifications {{
            channels(filters: {{ name: "{name}" }}) {{
              entities {{ id name }}
            }}
          }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    entities = (
        data.get("data", {})
        .get("actor", {})
        .get("account", {})
        .get("aiNotifications", {})
        .get("channels", {})
        .get("entities", [])
    )
    matches = [e for e in entities if e.get("name") == name]
    assert matches, f"No notification channel found with name '{name}'"
    print(f"  OK channel: '{name}' (id={matches[0]['id']})")


def test_workflow_exists():
    """`newrelic_workflow.placeholder_workflow` — queried via aiWorkflows.workflows."""
    name = f"{APP_NAME} - Placeholder Workflow"
    graphql = f"""
    {{
      actor {{
        account(id: {ACCOUNT_ID}) {{
          aiWorkflows {{
            workflows(filters: {{ name: "{name}" }}) {{
              entities {{ id name }}
            }}
          }}
        }}
      }}
    }}
    """
    data = query_nerdgraph(graphql)
    entities = (
        data.get("data", {})
        .get("actor", {})
        .get("account", {})
        .get("aiWorkflows", {})
        .get("workflows", {})
        .get("entities", [])
    )
    matches = [e for e in entities if e.get("name") == name]
    assert matches, f"No workflow found with name '{name}'"
    print(f"  OK workflow: '{name}' (id={matches[0]['id']})")


# ---------------------------------------------------------------------------
# Group B: cluster telemetry from helm install
# ---------------------------------------------------------------------------

def test_cluster_sample_reporting():
    """nri-bundle's kube-state-metrics integration reports K8sClusterSample."""
    nrql = (
        f"SELECT count(*) AS c FROM K8sClusterSample "
        f"WHERE clusterName = '{AKS_CLUSTER_NAME}' SINCE 10 minutes ago LIMIT 1"
    )
    results = run_nrql(nrql)
    count = (results[0].get("c") if results else 0) or 0
    assert count > 0, (
        f"No K8sClusterSample for clusterName='{AKS_CLUSTER_NAME}' in last 10 minutes. "
        "Is nri-bundle running and reporting?"
    )
    print(f"  OK K8sClusterSample count={count} for clusterName='{AKS_CLUSTER_NAME}'")


def test_newrelic_namespace_pods_reporting():
    """nri-bundle agent pods themselves visible in K8sPodSample (end-to-end sanity)."""
    nrql = (
        f"SELECT count(*) AS c FROM K8sPodSample "
        f"WHERE clusterName = '{AKS_CLUSTER_NAME}' AND namespace = 'newrelic' "
        f"SINCE 10 minutes ago LIMIT 1"
    )
    results = run_nrql(nrql)
    count = (results[0].get("c") if results else 0) or 0
    assert count > 0, (
        f"No K8sPodSample for namespace='newrelic' on cluster='{AKS_CLUSTER_NAME}' "
        "in last 10 minutes. The NR agent pods exist but are not being scraped."
    )
    print(f"  OK K8sPodSample count={count} for namespace='newrelic'")

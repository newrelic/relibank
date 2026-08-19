"""
Post-apply validation for the ReliBank NR workflow.

Confirms two things after `relibank-newrelic.yml` runs `terraform apply`:

  1. The entities/policies/conditions/destinations/channels/workflows created by the
     `newrelic/newrelic` provider (terraform/aks/newrelic/*.tf) are present in NR,
     queryable from the API user's perspective. One test per resource, parametrized
     by category so new resources can be added to a list rather than hand-written.
  2. The cluster-side helm releases installed by the same apply (`nri-bundle`,
     `nr-ebpf-agent`) are actually reporting telemetry — K8sClusterSample for
     the cluster, K8sPodSample for the `newrelic` namespace.

Group A's resource lists must be kept in sync with terraform/aks/newrelic/*.tf by
hand — there's no introspection of the .tf files here, just the names/types each
resource is expected to register under in NR.

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
# Group A: resources created by terraform/aks/newrelic/*.tf
# ---------------------------------------------------------------------------

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


def assert_alert_policy_exists(name):
    """Queried via alerts.policiesSearch (alert policies aren't `entitySearch`-able)."""
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


def assert_nrql_condition_exists(name):
    """Queried via alerts.nrqlConditionsSearch."""
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


def assert_notification_destination_exists(name):
    """Queried via aiNotifications.destinations."""
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


def assert_notification_channel_exists(name):
    """Queried via aiNotifications.channels."""
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


def assert_workflow_exists(name):
    """Queried via aiWorkflows.workflows."""
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


# `newrelic_one_dashboard_json.*` — dashboard's own top-level "name", not a widget title.
DASHBOARDS = [
    "ReliBank Summary",
    "Relibank BillPay Metrics",
]

# `newrelic_workload.*` — hardcoded names, no app_name prefix.
WORKLOADS = [
    "ReliBank - AI & Digital Experience Components",
    "ReliBank - Core Banking Components",
    "ReliBank - Payments & Transaction Components",
    "ReliBank - Platform Components",
]

# `newrelic_synthetics_script_monitor.*` — the only synthetics monitor this module creates.
SYNTHETICS_MONITORS = [
    f"{APP_NAME} - Login Check",
]

# `newrelic_alert_policy.*` — hardcoded names, no app_name prefix.
ALERT_POLICIES = [
    "ReliBank - AI & Digital Experience Policy",
    "ReliBank - Core Banking Policy",
    "ReliBank - Payments & Transactions Policy",
    "ReliBank - Platform Policy",
    "ReliBank - Before Autopilot Policy",
    "ReliBank - Autopilot + Workflow Automation Policy",
]

# `newrelic_nrql_alert_condition.*` — one representative condition per policy above,
# not an exhaustive list of the ~25 conditions nr_alerts.tf defines.
NRQL_ALERT_CONDITIONS = [
    "AIDE - High Response Time",
    "Core Banking - High Response Time",
    "Payments & Transactions - High Response Time",
    "Platform - High Response Time",
    "Legacy chat_with_model - High Transaction Error Rate",
    "WA: ReliBank Bill Pay - 403 Error",
]

# `newrelic_notification_destination.*`
NOTIFICATION_DESTINATIONS = [
    "github_scale_relibank_service_destination",
]

# `newrelic_notification_channel.*`
NOTIFICATION_CHANNELS = [
    "autopilot_channel",
    "staging_slack_channel",
    "before_autopilot_slack_channel",
    "github_scale_relibank_service Channel",
    "autopilot_plus_wa_channel",
]

# `newrelic_workflow.*`
WORKFLOWS = [
    "autopilot_and_slack_workflow",
    "before_autopilot_workflow",
    "Autopilot + Workflow Automation Workflow",
]


@pytest.mark.parametrize("name", DASHBOARDS)
def test_dashboard_exists(name):
    assert_entity_exists(name, "DASHBOARD")


@pytest.mark.parametrize("name", WORKLOADS)
def test_workload_exists(name):
    assert_entity_exists(name, "WORKLOAD")


@pytest.mark.parametrize("name", SYNTHETICS_MONITORS)
def test_synthetics_monitor_exists(name):
    assert_entity_exists(name, "MONITOR")


@pytest.mark.parametrize("name", ALERT_POLICIES)
def test_alert_policy_exists(name):
    assert_alert_policy_exists(name)


@pytest.mark.parametrize("name", NRQL_ALERT_CONDITIONS)
def test_nrql_alert_condition_exists(name):
    assert_nrql_condition_exists(name)


@pytest.mark.parametrize("name", NOTIFICATION_DESTINATIONS)
def test_notification_destination_exists(name):
    assert_notification_destination_exists(name)


@pytest.mark.parametrize("name", NOTIFICATION_CHANNELS)
def test_notification_channel_exists(name):
    assert_notification_channel_exists(name)


@pytest.mark.parametrize("name", WORKFLOWS)
def test_workflow_exists(name):
    assert_workflow_exists(name)


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

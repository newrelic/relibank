#!/usr/bin/env python3
"""
Test New Relic AI Agent monitoring (LlmAgent/LlmTool) for the support-service multi-agent flow.

Regression coverage for a real incident: a malformed `timestamp` field (an ISO-format string
instead of epoch milliseconds) on several of our own custom events (AgentToAgentCall,
LangGraphAgentInvocation, AgentInvocation, LangGraphWorkflowInvocation) broke thrift
serialization for the *entire* custom-event batch at New Relic's ingest layer, silently
discarding every custom event sent alongside it -- including LlmAgent/LlmTool. The request
itself always returned 200, so a pure request-success check never would have caught this; only
checking NRDB for the actual events does.

Prerequisites:
- NEW_RELIC_USER_API_KEY environment variable
- NEW_RELIC_ACCOUNT_ID environment variable (defaults to 4182956)
- support-service running with New Relic instrumentation
"""

import os
import time
import pytest
import requests
from pathlib import Path
from typing import Dict, List

from nrql_color import color_filter


# Helper function to load environment variables from skaffold.env if present
def load_env_from_skaffold():
    """Load environment variables from skaffold.env if file exists (local development)"""
    skaffold_env_path = Path(__file__).parent.parent / "skaffold.env"
    if skaffold_env_path.exists():
        with open(skaffold_env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    # Only set if not already in environment (explicit env vars take precedence)
                    if key not in os.environ:
                        os.environ[key] = value


# Load from skaffold.env if present (for local development)
load_env_from_skaffold()

# Configuration
SUPPORT_SERVICE_URL = os.getenv("SUPPORT_SERVICE_URL", "http://localhost:5003")
NEW_RELIC_API_KEY = os.getenv("NEW_RELIC_USER_API_KEY")
NEW_RELIC_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "4182956")
NERDGRAPH_URL = "https://api.newrelic.com/graphql"

# LlmAgent/LlmTool carry no deploy-color dimension of their own (no k8s namespace or deploy.color
# attribute in the payload -- confirmed directly from the agent's audit log during the
# investigation that led to this test), so color_filter() can't be applied to them directly. The
# base tests below are intentionally env-level, scoped by a short SINCE window around the
# triggering request. Where a specific color IS directed (TARGET_COLOR set), the sibling `Span`
# event (which nri-metadata-injection does stamp with k8s.namespace.name) is used as a
# color-bearing proxy, correlated back to LlmAgent/LlmTool via the shared trace_id/trace.id --
# see get_colored_trace_ids() -- as a best-effort check, not a hard requirement.

# Skip all tests if New Relic credentials not provided
pytestmark = pytest.mark.skipif(
    not NEW_RELIC_API_KEY,
    reason="NEW_RELIC_USER_API_KEY environment variable not set"
)


def query_nerdgraph(nrql_query: str) -> List[Dict]:
    """Execute a NRQL query via NerdGraph API"""
    graphql_query = """
    query($accountId: Int!, $nrql: Nrql!) {
      actor {
        account(id: $accountId) {
          nrql(query: $nrql) {
            results
          }
        }
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "API-Key": NEW_RELIC_API_KEY
    }

    variables = {
        "accountId": int(NEW_RELIC_ACCOUNT_ID),
        "nrql": nrql_query
    }

    response = requests.post(
        NERDGRAPH_URL,
        headers=headers,
        json={"query": graphql_query, "variables": variables},
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"NerdGraph query failed: {response.status_code} - {response.text}")

    data = response.json()
    return data.get("data", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])


def query_nerdgraph_until(
    nrql_query: str, count_key: str, min_count: int = 1, max_wait: int = 60, interval: int = 5
) -> List[Dict]:
    """Poll a NRQL count query until count_key is >= min_count or max_wait elapses.

    LlmAgent/LlmTool ingestion lag observed up to ~1 minute during the original investigation,
    longer than the 30s default used elsewhere in this suite -- hence the longer max_wait here.
    Ingestion of multiple events from the same request can also be staggered (confirmed in CI:
    a poll that stops at the first nonzero count caught only 1 of 3 expected LlmAgent events) --
    min_count lets callers wait for the full expected set, not just "something landed".
    """
    elapsed = 0
    while True:
        results = query_nerdgraph(nrql_query)
        if results and results[0].get(count_key, 0) >= min_count:
            return results
        if elapsed >= max_wait:
            return results
        time.sleep(interval)
        elapsed += interval


def trigger_support_chat(message: str) -> Dict:
    """Send a real request through the Coordinator -> Specialist -> Synthesizer flow."""
    response = requests.post(
        f"{SUPPORT_SERVICE_URL}/support-service/assistant/chat",
        json={"message": message},
        timeout=60
    )
    return {
        "status_code": response.status_code,
        "body": response.json() if response.status_code == 200 else None
    }


def get_colored_trace_ids(span_name_pattern: str, color: str, since_minutes: int = 3) -> List[str]:
    """Best-effort: trace IDs for spans matching `span_name_pattern` within `color`'s namespace.

    LlmAgent/LlmTool carry no color dimension of their own (see module note above), so this uses
    the sibling `Span` data -- which nri-metadata-injection does stamp with k8s.namespace.name --
    as a color-bearing proxy. The same trace_id is shared by the whole request (agents and
    tools alike), so one span pattern (the agent ainvoke spans) is enough to color-tag any
    LlmAgent/LlmTool event from that request.
    """
    nrql = (
        f"SELECT uniques(trace.id) AS trace_ids FROM Span "
        f"WHERE name LIKE '{span_name_pattern}' {color_filter('Span')} "
        f"SINCE {since_minutes} minutes ago"
    )
    results = query_nerdgraph(nrql)
    if not results:
        return []
    return results[0].get("trace_ids", []) or []


def check_color_correlation(event_type: str, target_color: str) -> None:
    """Best-effort color-correlation check -- logs the outcome, never fails the test.

    Only meaningful when a specific color is directed (TARGET_COLOR set); the base event-count
    assertions in each test already cover the undirected case.
    """
    print(f"\n4. Verifying {event_type} events correlate to target color '{target_color}' (best-effort)...")
    trace_ids = get_colored_trace_ids("Llm/agent/LangChain/ainvoke/%", target_color)

    if not trace_ids:
        print(
            f"   ⚠️  No colored Span trace IDs found for '{target_color}' within the polling "
            "window -- skipping color-correlation (base event-count assertion above already passed)"
        )
        return

    quoted_ids = ", ".join(f"'{tid}'" for tid in trace_ids)
    results = query_nerdgraph(
        f"SELECT count(*) AS colored_count FROM {event_type} "
        f"WHERE trace_id IN ({quoted_ids}) SINCE 5 minutes ago"
    )
    colored_count = results[0].get("colored_count", 0) if results else 0

    if colored_count > 0:
        print(f"   ✅ {colored_count} {event_type} event(s) correlated to color '{target_color}'")
    else:
        print(
            f"   ⚠️  Found colored Spans but no matching {event_type} trace_id -- "
            "skipping (base event-count assertion above already passed)"
        )


def test_llm_agent_events_populate(target_color):
    """
    Verify LlmAgent events reach NRDB for the Coordinator/Specialist/Synthesizer agents.

    See module docstring for the known failure mode this guards against.
    """
    print("\n" + "=" * 80)
    print("TEST: LlmAgent events populate in New Relic")
    print("=" * 80)

    print("\n1. Triggering support-service assistant chat...")
    result = trigger_support_chat("What is a certificate of deposit?")
    assert result["status_code"] == 200, f"Expected 200, got {result['status_code']}"
    print(f"   ✓ Request succeeded (status: {result['status_code']})")

    print("\n2. Querying New Relic for LlmAgent events (polling up to 90s for all 3 agents to land)...")
    nrql = (
        "SELECT count(*) AS agent_count, uniques(name) AS agent_names "
        "FROM LlmAgent SINCE 3 minutes ago"
    )
    # min_count=3: coordinator/specialist/synthesizer ingest can land staggered across harvest
    # cycles -- stopping at the first nonzero count risks asserting on a partial result.
    results = query_nerdgraph_until(nrql, "agent_count", min_count=3, max_wait=90)

    agent_count = results[0].get("agent_count", 0) if results else 0
    agent_names = results[0].get("agent_names", []) if results else []
    print("\n3. Results:")
    print(f"   LlmAgent events found: {agent_count}")
    print(f"   Agent names: {agent_names}")

    assert agent_count > 0, (
        f"Expected LlmAgent events after a support-service chat request, found {agent_count}. "
        "If this regresses, check for malformed fields (e.g. a non-numeric 'timestamp') on any "
        "custom event recorded in the same request -- a single bad event can silently drop the "
        "entire custom-event batch at ingest, including LlmAgent/LlmTool."
    )

    for expected_agent in ("coordinator", "specialist", "synthesizer"):
        assert expected_agent in agent_names, (
            f"Expected an LlmAgent event named '{expected_agent}', got names: {agent_names}"
        )

    print(f"\n✅ PASS: Found {agent_count} LlmAgent events ({', '.join(agent_names)})")

    if target_color:
        check_color_correlation("LlmAgent", target_color)


def test_llm_tool_events_populate(target_color):
    """
    Verify LlmTool events reach NRDB for the delegate_to_specialist tool.

    Same regression coverage as test_llm_agent_events_populate, for the tool-call side.
    """
    print("\n" + "=" * 80)
    print("TEST: LlmTool events populate in New Relic")
    print("=" * 80)

    print("\n1. Triggering support-service assistant chat...")
    result = trigger_support_chat("What is a money market account?")
    assert result["status_code"] == 200, f"Expected 200, got {result['status_code']}"
    print(f"   ✓ Request succeeded (status: {result['status_code']})")

    print("\n2. Querying New Relic for LlmTool events (polling up to 60s for ingestion)...")
    nrql = (
        "SELECT count(*) AS tool_count, latest(name) AS tool_name "
        "FROM LlmTool SINCE 3 minutes ago"
    )
    results = query_nerdgraph_until(nrql, "tool_count")

    tool_count = results[0].get("tool_count", 0) if results else 0
    tool_name = results[0].get("tool_name") if results else None
    print("\n3. Results:")
    print(f"   LlmTool events found: {tool_count}")
    print(f"   Tool name: {tool_name}")

    assert tool_count > 0, (
        f"Expected LlmTool events after a support-service chat request, found {tool_count}. "
        "See test_llm_agent_events_populate docstring for the known failure mode."
    )
    assert tool_name == "delegate_to_specialist", (
        f"Expected LlmTool event for 'delegate_to_specialist', got '{tool_name}'"
    )

    print(f"\n✅ PASS: Found {tool_count} LlmTool event(s) for '{tool_name}'")

    if target_color:
        check_color_correlation("LlmTool", target_color)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

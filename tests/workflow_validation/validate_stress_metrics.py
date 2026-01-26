#!/usr/bin/env python3
"""
Validate stress chaos experiments by checking New Relic metrics.

This script queries New Relic to verify that stress experiments are actually
impacting the target services as expected.
"""

import sys
import os
import requests
import json

# Scenario to service mapping
SCENARIO_TARGETS = {
    "relibank-cpu-stress-test": {
        "service": "transaction-service",
        "metric": "cpuUsedCores",
        "threshold": 0.5,  # 0.5 CPU cores
        "stress_type": "CPU",
        "unit": "cores"
    },
    "relibank-high-cpu-stress": {
        "service": "transaction-service",
        "metric": "cpuUsedCores",
        "threshold": 0.95,  # 0.95 CPU cores
        "stress_type": "High CPU",
        "unit": "cores"
    },
    "relibank-memory-stress-test": {
        "service": "bill-pay-service",
        "metric": "memoryWorkingSetBytes",
        "threshold": 268435456,  # 256MB in bytes
        "stress_type": "Memory",
        "unit": "bytes"
    },
    "relibank-high-memory-stress": {
        "service": "bill-pay-service",
        "metric": "memoryWorkingSetBytes",
        "threshold": 536870912,  # 512MB in bytes
        "stress_type": "High Memory",
        "unit": "bytes"
    },
    "relibank-combined-stress-test": {
        "service": "transaction-service",
        "metric": "cpuUsedCores",
        "threshold": 0.5,  # 0.5 CPU cores
        "stress_type": "Combined (CPU check)",
        "unit": "cores"
    }
}


def query_new_relic_metrics(scenario_name, nr_api_key, nr_account_id, wait_minutes=5):
    """
    Query New Relic for metrics to validate stress is applied.

    Args:
        scenario_name: Name of the stress scenario
        nr_api_key: New Relic User API key
        nr_account_id: New Relic account ID
        wait_minutes: How many minutes of data to analyze

    Returns:
        dict: Validation results with success status and metrics
    """

    if scenario_name not in SCENARIO_TARGETS:
        return {
            "success": False,
            "error": f"Unknown scenario: {scenario_name}",
            "valid_scenarios": list(SCENARIO_TARGETS.keys())
        }

    target = SCENARIO_TARGETS[scenario_name]
    service = target["service"]
    metric = target["metric"]
    threshold = target["threshold"]
    stress_type = target["stress_type"]
    unit = target.get("unit", "percent")

    print(f"\n=== Validating Stress Scenario ===")
    print(f"Scenario: {scenario_name}")
    print(f"Target Service: {service}")
    print(f"Metric: {metric}")
    if unit == "bytes":
        print(f"Threshold: {threshold / (1024**2):.0f}MB ({threshold} bytes)")
    elif unit == "cores":
        print(f"Threshold: {threshold} CPU cores")
    else:
        print(f"Threshold: {threshold}%")
    print(f"Stress Type: {stress_type}")
    print(f"Analysis Window: Last {wait_minutes} minutes")

    # Build NRQL query (single line for GraphQL embedding)
    nrql = f"SELECT average({metric}) as avgUsage, max({metric}) as maxUsage, min({metric}) as minUsage, percentile({metric}, 95) as p95Usage FROM K8sContainerSample WHERE containerName = '{service}' AND clusterName LIKE '%relibank%' SINCE {wait_minutes} minutes ago"

    print(f"\nNRQL Query:\n{nrql}")

    # GraphQL query
    graphql_query = {
        "query": f"""
        {{
            actor {{
                account(id: {nr_account_id}) {{
                    nrql(query: "{nrql}") {{
                        results
                    }}
                }}
            }}
        }}
        """
    }

    # Execute query
    try:
        response = requests.post(
            "https://api.newrelic.com/graphql",
            headers={
                "Content-Type": "application/json",
                "API-Key": nr_api_key
            },
            json=graphql_query,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to query New Relic: {str(e)}"
        }

    # Parse results
    try:
        results = data["data"]["actor"]["account"]["nrql"]["results"]

        if not results or len(results) == 0:
            return {
                "success": False,
                "error": f"No metrics found for {service}. Service may not be reporting to New Relic.",
                "service": service
            }

        metrics = results[0]

        # Handle null values (service might not be reporting this metric)
        avg_usage_raw = metrics.get("avgUsage")
        max_usage_raw = metrics.get("maxUsage")
        min_usage_raw = metrics.get("minUsage")
        p95_usage_raw = metrics.get("p95Usage")

        # Check if all metrics are null
        if all(v is None for v in [avg_usage_raw, max_usage_raw, min_usage_raw]):
            return {
                "success": False,
                "error": f"Metric '{metric}' not found for {service}. Check metric name or service reporting.",
                "service": service,
                "metric": metric,
                "hint": "Common metrics: cpuUsedCores, cpuCoresUtilization, memoryUsedBytes, memoryWorkingSetBytes"
            }

        avg_usage = float(avg_usage_raw) if avg_usage_raw is not None else 0.0
        max_usage = float(max_usage_raw) if max_usage_raw is not None else 0.0
        min_usage = float(min_usage_raw) if min_usage_raw is not None else 0.0

        # p95Usage might be a dict with percentile key
        if isinstance(p95_usage_raw, dict):
            p95_usage = float(p95_usage_raw.get("95", 0))
        else:
            p95_usage = float(p95_usage_raw) if p95_usage_raw is not None else 0.0

    except (KeyError, ValueError, TypeError) as e:
        return {
            "success": False,
            "error": f"Failed to parse New Relic response: {str(e)}",
            "response": data
        }

    # Display results
    print(f"\n=== Metrics Analysis ===")
    if unit == "bytes":
        print(f"Average {stress_type}: {avg_usage / (1024**2):.2f}MB ({avg_usage:.0f} bytes)")
        print(f"Maximum {stress_type}: {max_usage / (1024**2):.2f}MB ({max_usage:.0f} bytes)")
        print(f"Minimum {stress_type}: {min_usage / (1024**2):.2f}MB ({min_usage:.0f} bytes)")
        print(f"95th Percentile: {p95_usage / (1024**2):.2f}MB ({p95_usage:.0f} bytes)")
    elif unit == "cores":
        print(f"Average {stress_type}: {avg_usage:.3f} cores")
        print(f"Maximum {stress_type}: {max_usage:.3f} cores")
        print(f"Minimum {stress_type}: {min_usage:.3f} cores")
        print(f"95th Percentile: {p95_usage:.3f} cores")
    else:
        print(f"Average {stress_type}: {avg_usage:.2f}%")
        print(f"Maximum {stress_type}: {max_usage:.2f}%")
        print(f"Minimum {stress_type}: {min_usage:.2f}%")
        print(f"95th Percentile: {p95_usage:.2f}%")

    # Validate stress was applied
    stress_detected = max_usage > threshold

    print(f"\n=== Validation Result ===")
    if stress_detected:
        print(f"✓ STRESS DETECTED!")
        if unit == "bytes":
            print(f"  Max {stress_type} ({max_usage / (1024**2):.2f}MB) exceeds threshold ({threshold / (1024**2):.0f}MB)")
        elif unit == "cores":
            print(f"  Max {stress_type} ({max_usage:.3f} cores) exceeds threshold ({threshold} cores)")
        else:
            print(f"  Max {stress_type} ({max_usage:.2f}%) exceeds threshold ({threshold}%)")
        print(f"  Stress scenario is working as expected")
    else:
        print(f"⚠ STRESS NOT CLEARLY DETECTED")
        if unit == "bytes":
            print(f"  Max {stress_type} ({max_usage / (1024**2):.2f}MB) below threshold ({threshold / (1024**2):.0f}MB)")
        elif unit == "cores":
            print(f"  Max {stress_type} ({max_usage:.3f} cores) below threshold ({threshold} cores)")
        else:
            print(f"  Max {stress_type} ({max_usage:.2f}%) below threshold ({threshold}%)")
        print(f"\n  Possible reasons:")
        print(f"  - Stress experiment didn't apply (check Chaos Mesh logs)")
        print(f"  - Container runtime incompatibility (requires containerd)")
        print(f"  - Service has high baseline usage")
        print(f"  - New Relic metrics delayed")

    return {
        "success": stress_detected,
        "scenario": scenario_name,
        "service": service,
        "stress_type": stress_type,
        "metric": metric,
        "threshold": threshold,
        "avg_usage": avg_usage,
        "max_usage": max_usage,
        "min_usage": min_usage,
        "p95_usage": p95_usage,
        "stress_detected": stress_detected
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_stress_metrics.py <scenario_name> [wait_minutes]")
        print("\nAvailable scenarios:")
        for scenario in SCENARIO_TARGETS.keys():
            target = SCENARIO_TARGETS[scenario]
            print(f"  - {scenario} (targets {target['service']})")
        sys.exit(1)

    scenario_name = sys.argv[1]
    wait_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    # Get credentials from environment
    nr_api_key = os.environ.get("NEW_RELIC_API_KEY")
    nr_account_id = os.environ.get("NEW_RELIC_ACCOUNT_ID")

    if not nr_api_key or not nr_account_id:
        print("Error: NEW_RELIC_API_KEY and NEW_RELIC_ACCOUNT_ID environment variables required")
        sys.exit(1)

    result = query_new_relic_metrics(scenario_name, nr_api_key, nr_account_id, wait_minutes)

    print(f"\n=== Final Result ===")
    print(json.dumps(result, indent=2))

    sys.exit(0 if result["success"] else 1)

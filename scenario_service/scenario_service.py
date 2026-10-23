# NOTE: importing `locust` at module level pulls in gevent and triggers
# `monkey.patch_all()`, which replaces stdlib `threading` / `socket` /
# `ssl` with green-thread equivalents. That breaks db-360's pyodbc workers
# (they become greenlets and block the event loop on each blocking SQL call).
# `locust.main` is only needed inside the /run_locust handler — defer the
# import to that callsite so gevent never patches this process for the
# common case where Locust isn't being used.
import os
import copy
import uuid
import yaml
from pathlib import Path
import sys
import asyncio
import logging
import threading
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import httpx
import pyodbc

# Custom logging filter to suppress repetitive health check / config endpoint logs
class HealthCheckFilter(logging.Filter):
    """Suppress repetitive INFO logs for health check and config endpoints"""
    def filter(self, record: logging.LogRecord) -> bool:
        # Suppress INFO-level logs for config endpoints that get polled frequently
        if record.levelno == logging.INFO:
            message = record.getMessage()
            if 'GET /scenario-runner/api/dem-memory-leak/config' in message:
                return False
            if 'GET /scenario-runner/api/ab-testing/config' in message:
                return False
            if 'GET /scenario-runner/api/payment-scenarios/config' in message:
                return False
        return True

# Apply the filter to uvicorn's access logger
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

# Deploy-time flag: whether the browser UI (/scenario-runner/home) is exposed.
# The scenario API (/scenario-runner/api/*) is always reachable regardless.
# Read once at startup; toggling requires a redeploy that rolls this pod.
SCENARIO_UI_ENABLED = os.getenv("SCENARIO_UI_ENABLED", "true").lower() == "true"

# Dictionary to store parsed Chaos Mesh experiments
CHAOS_EXPERIMENTS: Dict[str, Dict[str, Any]] = {}
STRESS_EXPERIMENTS: Dict[str, Dict[str, Any]] = {}
# NetworkChaos / DNSChaos experiments (loaded from relibank-network-scenarios.yaml)
NETWORK_EXPERIMENTS: Dict[str, Dict[str, Any]] = {}
NETWORK_CHAOS_PLURALS = {"NetworkChaos": "networkchaos", "DNSChaos": "dnschaos"}

# Kubernetes API clients for custom resources
api_client = None
api_version = "chaos-mesh.org/v1alpha1"
plural = "podchaos"
stress_plural = "stresschaos"

# Payment scenario configuration (runtime toggleable)
PAYMENT_SCENARIOS = {
    "gateway_timeout_enabled": False,
    "gateway_timeout_delay": 10.0,
    "gateway_timeout_probability": 0.0,  # 0-100 percent
    "card_decline_enabled": False,
    "card_decline_probability": 0.0,  # 0-100 percent
    "stolen_card_enabled": False,
    "stolen_card_probability": 0.0,  # 0-100 percent
}

# Risk assessment scenario configuration (runtime toggleable)
RISK_ASSESSMENT_SCENARIOS = {
    "rogue_agent_enabled": False,  # When true, uses gpt-4o-mini (stringent), when false uses gpt-4o (normal)
    "agent_name": "gpt-4o",  # Current agent: "gpt-4o" or "gpt-4o-mini"
}

# A/B Testing scenario configuration (runtime toggleable)
# Hardcoded list of 11 test users who will experience LCP slowness when cohort scenario is enabled
LCP_SLOW_USERS = {
    'b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d',  # Alice Johnson
    'f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a',  # Bob Williams
    'e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b',  # Charlie Brown
    'f47ac10b-58cc-4372-a567-0e02b2c3d471',  # Solaire Astora
    'd9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a',  # Malenia Miquella
    '8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f',  # Artorias Abyss
    '7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f',  # Priscilla Painted
    '6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a',  # Gwyn Cinder
    '5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b',  # Siegmeyer Catarina
    '4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c',  # Ornstein Dragon
    '3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d',  # Smough Executioner
}

AB_TEST_SCENARIOS = {
    # Percentage-based scenario (50% of all users)
    "lcp_slowness_percentage_enabled": False,
    "lcp_slowness_percentage": 50.0,  # 0-100 percent of users
    "lcp_slowness_percentage_delay_ms": 3000,  # Milliseconds of delay

    # Cohort-based scenario (11 hardcoded test users)
    "lcp_slowness_cohort_enabled": False,
    "lcp_slowness_cohort_delay_ms": 3000,  # Milliseconds of delay
    "lcp_slowness_cohort_user_count": len(LCP_SLOW_USERS),  # Number of users in cohort

    # Database pool stress scenario (affects 50% of users on pool-a)
    "db_pool_stress_enabled": False,
    "db_pool_stress_delay_ms": 500,  # How long to hold each connection (milliseconds)
    "db_pool_stress_affected_pool": "pool-a",  # Which pool is affected (pool-a or pool-b)
}

# Memory Leak Scenarios
DEM_FORRESTER_SCENARIOS = {
    # Persistent toggle scenario
    "memory_leak_toggle_enabled": False,
    "memory_leak_rate_mb_per_sec": 0.44,  # MB allocated per second (~30 min climb to 800 MB)
    "memory_leak_max_mb": 800,  # Maximum memory to allocate before capping

    # One-time trigger scenario (45-min: 30-min climb + 15-min hold)
    "memory_leak_trigger_active": False,
    "memory_leak_trigger_deadline": None,  # Unix timestamp (time.time()) when it should stop
    "memory_leak_trigger_duration_sec": 2700,  # 45 minutes (2700 seconds) - 30 min climb + 15 min hold

    # Second trigger scenario (25-min: 10-min climb + 15-min hold)
    "memory_leak_trigger_10min_active": False,
    "memory_leak_trigger_10min_deadline": None,  # Unix timestamp (time.time()) when it should stop
    "memory_leak_trigger_10min_duration_sec": 1500,  # 25 minutes (1500 seconds) - 10 min climb + 15 min hold
    "memory_leak_trigger_10min_rate": 1.33,  # MB allocated per second (~10 min climb to 800 MB)
}

# Rate limiting for chaos scenarios (abuse prevention)
# Use shorter cooldown for local development environments
def get_cooldown_minutes():
    """Determine cooldown based on environment (1 min local, 5 min production)"""
    try:
        config.load_incluster_config()
        return 5  # Running in-cluster (production)
    except config.ConfigException:
        return 1  # Running locally with kube config

CHAOS_RATE_LIMIT = {
    "last_trigger_time": None,
    "cooldown_minutes": get_cooldown_minutes(),  # 1 min local, 5 min production
    "max_concurrent": 3,    # Maximum concurrent chaos experiments allowed (pod + stress)
    "active_experiments": 0  # Counter for active chaos experiments
}


def get_current_namespace(default: str = "relibank") -> str:
    """The namespace this pod is actually running in.

    Terraform-managed envs (sandbox/staging/prod) are blue/green
    (``relibank-blue``/``relibank-green``), while legacy envs (events) are a
    single ``relibank`` namespace. The chaos-mesh experiment YAMLs hardcode
    ``relibank``, which silently matches zero pods on a blue/green cluster
    ("no pods matched selector"). Every pod gets its own namespace mounted by
    the serviceaccount token by default, so read that instead of trusting the
    YAML — this keeps chaos scenarios working regardless of which env/color
    scenario-service itself is deployed into.
    """
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip() or default
    except OSError:
        return default


def _selector_pod_count(selector: dict) -> int:
    """How many live pods a chaos/stress selector would actually match, without
    creating any chaos-mesh resource. Backs the trigger endpoints' `dry_run`
    option — catches selector/namespace drift (e.g. a hardcoded namespace that
    doesn't exist on this cluster) before it silently no-ops a real experiment.
    """
    core_v1 = client.CoreV1Api()
    label_selectors = selector.get("labelSelectors", {})
    label_selector_str = ",".join(f"{k}={v}" for k, v in label_selectors.items())
    total = 0
    for namespace in selector.get("namespaces", []):
        try:
            pods = core_v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector_str)
            total += len(pods.items)
        except ApiException as e:
            print(f"WARNING: dry-run pod lookup failed for namespace '{namespace}': {e}")
    return total

# Define the lifespan of the application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Loads chaos experiment definitions on application startup and initializes Kubernetes client.
    """
    global api_client

    current_namespace = get_current_namespace()
    print(f"INFO: Chaos experiments will target namespace '{current_namespace}' (this pod's own namespace)")

    base_dir = Path(__file__).parent.absolute()
    pod_chaos_file = base_dir / "chaos_mesh" / "experiments" / "relibank-pod-chaos-adhoc.yaml"
    stress_chaos_file = base_dir / "chaos_mesh" / "experiments" / "relibank-stress-scenarios.yaml"
    network_chaos_file = base_dir / "chaos_mesh" / "experiments" / "relibank-network-scenarios.yaml"

    loaded_count = 0 # Initialize counter for successful loads

    # Load and parse the pod chaos experiment YAML file
    try:
        print(f"INFO: Attempting to read pod chaos YAML from: {pod_chaos_file}")

        with open(pod_chaos_file, 'r') as file:
            # Use safe_load_all for multi-document YAML
            for i, doc in enumerate(yaml.safe_load_all(file)):
                if doc:
                    current_kind = doc.get('kind', 'N/A')
                    current_name = doc.get('metadata', {}).get('name', 'N/A')
                    print(f"DEBUG: Parsed document {i}. Kind: {current_kind}, Name: {current_name}")

                    if current_kind == "PodChaos":
                        name = doc["metadata"]["name"]
                        description = doc["metadata"].get("labels", {}).get("target-flow", "No description available.")

                        # Store the complete experiment spec for ad-hoc execution.
                        # Override the YAML's hardcoded namespace with wherever this
                        # pod actually runs (see get_current_namespace) so the
                        # selector matches real pods on blue/green clusters.
                        CHAOS_EXPERIMENTS[name] = {
                            "namespace": current_namespace,
                            "action": doc["spec"]["action"],
                            "mode": doc["spec"]["mode"],
                            "selector": {**doc["spec"]["selector"], "namespaces": [current_namespace]},
                            "duration": doc["spec"]["duration"],
                            "gracePeriod": doc["spec"]["gracePeriod"],
                            "description": description
                        }
                        loaded_count += 1
                    else:
                        print(f"DEBUG: Skipping document {i}. Kind is not 'PodChaos'.")
                else:
                    print(f"DEBUG: Skipping empty document {i}.")

    except FileNotFoundError:
        print(f"Error: The YAML file was not found at '{pod_chaos_file}'. This indicates a Dockerfile COPY issue.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}. Check YAML format.")

    # Load and parse the stress chaos experiment YAML file
    try:
        print(f"INFO: Attempting to read stress chaos YAML from: {stress_chaos_file}")

        with open(stress_chaos_file, 'r') as file:
            for i, doc in enumerate(yaml.safe_load_all(file)):
                if doc:
                    current_kind = doc.get('kind', 'N/A')
                    current_name = doc.get('metadata', {}).get('name', 'N/A')
                    print(f"DEBUG: Parsed stress document {i}. Kind: {current_kind}, Name: {current_name}")

                    if current_kind == "StressChaos":
                        name = doc["metadata"]["name"]
                        description = doc["metadata"].get("labels", {}).get("target-flow", "No description available.")

                        # Store the complete stress experiment spec. Override the
                        # YAML's hardcoded namespace the same way as CHAOS_EXPERIMENTS
                        # above, so this matches real pods on blue/green clusters.
                        STRESS_EXPERIMENTS[name] = {
                            "namespace": current_namespace,
                            "mode": doc["spec"]["mode"],
                            "selector": {**doc["spec"]["selector"], "namespaces": [current_namespace]},
                            "duration": doc["spec"]["duration"],
                            "stressors": doc["spec"]["stressors"],
                            # Optional: limits the stressors to specific containers (e.g. mssql)
                            "containerNames": doc["spec"].get("containerNames"),
                            "description": description
                        }
                        loaded_count += 1
                    else:
                        print(f"DEBUG: Skipping stress document {i}. Kind is not 'StressChaos'.")
                else:
                    print(f"DEBUG: Skipping empty stress document {i}.")

    except FileNotFoundError:
        print(f"Error: The stress YAML file was not found at '{stress_chaos_file}'.")
    except yaml.YAMLError as e:
        print(f"Error parsing stress YAML file: {e}. Check YAML format.")

    # Load and parse the network chaos experiment YAML file (NetworkChaos / DNSChaos)
    try:
        print(f"INFO: Attempting to read network chaos YAML from: {network_chaos_file}")

        with open(network_chaos_file, 'r') as file:
            for i, doc in enumerate(yaml.safe_load_all(file)):
                if not doc:
                    print(f"DEBUG: Skipping empty network document {i}.")
                    continue
                current_kind = doc.get('kind', 'N/A')
                if current_kind not in NETWORK_CHAOS_PLURALS:
                    print(f"DEBUG: Skipping network document {i}. Kind '{current_kind}' is not NetworkChaos/DNSChaos.")
                    continue

                name = doc["metadata"]["name"]
                description = doc["metadata"].get("labels", {}).get("target-flow", "No description available.")

                # Same namespace handling as the other kinds: target whichever namespace this
                # pod runs in, so selectors match real pods on blue/green clusters.
                spec = copy.deepcopy(doc["spec"])
                spec["selector"] = {**spec["selector"], "namespaces": [current_namespace]}
                if isinstance(spec.get("target"), dict) and "selector" in spec["target"]:
                    # NetworkChaos `target` peers are selected by namespace too
                    spec["target"] = {**spec["target"],
                                      "selector": {**spec["target"]["selector"], "namespaces": [current_namespace]}}
                if "patterns" in spec:
                    # DNSChaos patterns embed the namespace in the service FQDN
                    # (e.g. accounts-service.relibank.svc.cluster.local.)
                    spec["patterns"] = [p.replace(".relibank.", f".{current_namespace}.") for p in spec["patterns"]]

                NETWORK_EXPERIMENTS[name] = {
                    "kind": current_kind,
                    "namespace": current_namespace,
                    "selector": spec["selector"],
                    "duration": spec["duration"],
                    "spec": spec,
                    "description": description
                }
                loaded_count += 1

    except FileNotFoundError:
        print(f"Error: The network chaos YAML file was not found at '{network_chaos_file}'.")
    except yaml.YAMLError as e:
        print(f"Error parsing network chaos YAML file: {e}. Check YAML format.")

    # Initialize Kubernetes client from within the pod
    try:
        config.load_incluster_config()
    except config.ConfigException:
        print("Warning: Could not load in-cluster config. Loading kube config from default location.")
        config.load_kube_config()
    
    api_client = client.CustomObjectsApi()

    print(f"Chaos experiments loaded successfully on startup. Total: {loaded_count} experiments ({len(CHAOS_EXPERIMENTS)} pod chaos, {len(STRESS_EXPERIMENTS)} stress chaos, {len(NETWORK_EXPERIMENTS)} network/dns chaos)")
    yield
    # Cancel any in-flight db-360 workers and rollback open transactions before the
    # process exits — otherwise SIGTERM leaves UPDLOCK-holding sessions on MSSQL.
    _shutdown_db360()
    _shutdown_dbmatrix()
    _shutdown_noisy_neighbor()
    print("Application is shutting down.")

# Initialize FastAPI app with the lifespan
app = FastAPI(title="Relibank Scenario Runner", lifespan=lifespan)

@app.get("/scenario-runner/home", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page (gated by the SCENARIO_UI_ENABLED deploy flag)."""
    if not SCENARIO_UI_ENABLED:
        # Behave as if the page doesn't exist; the API remains reachable.
        raise HTTPException(status_code=404)
    with open("index.html", "r") as f:
        return f.read()

@app.get("/scenario-runner/api/scenarios", response_model=List[Dict[str, Any]])
async def get_scenarios():
    """Returns a list of available chaos scenarios and their details."""
    scenarios_list = []
    for name, details in CHAOS_EXPERIMENTS.items():
        # Extract target service from selector
        target_service = details.get("selector", {}).get("labelSelectors", {}).get("app", "unknown")
        scenarios_list.append({
            "name": name,
            "description": details["description"],
            "type": "chaos-mesh",
            "target_service": target_service
        })
    # Add stress chaos scenarios
    for name, details in STRESS_EXPERIMENTS.items():
        # Extract target service from selector
        target_service = details.get("selector", {}).get("labelSelectors", {}).get("app", "unknown")
        scenarios_list.append({
            "name": name,
            "description": details["description"],
            "type": "stress-chaos",
            "target_service": target_service
        })
    # Placeholder for future Locust scenarios
    scenarios_list.append({
        "name": "pay_cancel.py",
        "description": "Bill pay and cancel with a POST request.",
        "type": "locust"
    })
    # Payment scenarios
    scenarios_list.append({
        "name": "card_decline",
        "description": "Card Decline",
        "type": "payment",
        "enabled": PAYMENT_SCENARIOS["card_decline_enabled"],
        "config": {"probability": PAYMENT_SCENARIOS["card_decline_probability"]}
    })
    scenarios_list.append({
        "name": "gateway_timeout",
        "description": "Gateway Timeout",
        "type": "payment",
        "enabled": PAYMENT_SCENARIOS["gateway_timeout_enabled"],
        "config": {
            "delay": PAYMENT_SCENARIOS["gateway_timeout_delay"],
            "probability": PAYMENT_SCENARIOS["gateway_timeout_probability"]
        }
    })
    scenarios_list.append({
        "name": "stolen_card",
        "description": "Stolen Card",
        "type": "payment",
        "enabled": PAYMENT_SCENARIOS["stolen_card_enabled"],
        "config": {"probability": PAYMENT_SCENARIOS["stolen_card_probability"]}
    })
    # Risk Assessment scenarios (feature flag)
    scenarios_list.append({
        "name": "rogue_agent",
        "description": "Rogue AI Agent (Declines Most Payments)",
        "type": "feature_flag",
        "enabled": RISK_ASSESSMENT_SCENARIOS["rogue_agent_enabled"],
        "config": {"agent_name": RISK_ASSESSMENT_SCENARIOS["agent_name"]}
    })
    # A/B Testing scenarios
    scenarios_list.append({
        "name": "lcp_slowness_percentage",
        "description": "LCP Slowness A/B Test (Percentage-based)",
        "type": "ab_test",
        "enabled": AB_TEST_SCENARIOS["lcp_slowness_percentage_enabled"],
        "config": {
            "percentage": AB_TEST_SCENARIOS["lcp_slowness_percentage"],
            "delay_ms": AB_TEST_SCENARIOS["lcp_slowness_percentage_delay_ms"]
        }
    })
    scenarios_list.append({
        "name": "lcp_slowness_cohort",
        "description": "LCP Slowness A/B Test (Cohort-based - 11 users)",
        "type": "ab_test",
        "enabled": AB_TEST_SCENARIOS["lcp_slowness_cohort_enabled"],
        "config": {
            "user_count": AB_TEST_SCENARIOS["lcp_slowness_cohort_user_count"],
            "delay_ms": AB_TEST_SCENARIOS["lcp_slowness_cohort_delay_ms"]
        }
    })
    scenarios_list.append({
        "name": "db_pool_stress",
        "description": "Database Pool Performance Issue (50% of users)",
        "type": "ab_test",
        "enabled": AB_TEST_SCENARIOS["db_pool_stress_enabled"],
        "config": {
            "delay_ms": AB_TEST_SCENARIOS["db_pool_stress_delay_ms"],
            "affected_pool": AB_TEST_SCENARIOS["db_pool_stress_affected_pool"]
        }
    })
    # Network / DNS chaos scenarios
    for name, details in NETWORK_EXPERIMENTS.items():
        scenarios_list.append({
            "name": name,
            "description": details["description"],
            "type": "network-chaos",
            "target_service": details["selector"].get("labelSelectors", {}).get("app", "unknown"),
            "kind": details["kind"]
        })
    # Memory Leak scenarios
    scenarios_list.append({
        "name": "dem-memory-leak-45min",
        "description": "Memory Leak (45-min: 30-min climb + 15-min hold)",
        "type": "stress-chaos",
        "target_service": "accounts-service"
    })
    scenarios_list.append({
        "name": "dem-memory-leak-10min",
        "description": "Memory Leak (25-min: 10-min climb + 15-min hold)",
        "type": "stress-chaos",
        "target_service": "accounts-service"
    })
    scenarios_list.append({
        "name": "dem_memory_leak_toggle",
        "description": "Memory Leak (Manual Toggle)",
        "type": "ab_test",
        "enabled": DEM_FORRESTER_SCENARIOS["memory_leak_toggle_enabled"],
        "config": {
            "rate_mb_per_sec": DEM_FORRESTER_SCENARIOS["memory_leak_rate_mb_per_sec"],
            "max_mb": DEM_FORRESTER_SCENARIOS["memory_leak_max_mb"]
        }
    })
    return scenarios_list

@app.post("/scenario-runner/api/trigger_chaos/{scenario_name}")
async def trigger_chaos_experiment(scenario_name: str, dry_run: bool = False):
    """Triggers a one-time Chaos Mesh experiment with rate limiting.

    dry_run=true checks whether the scenario's selector would match any live
    pods right now — without creating a chaos-mesh resource, consuming the
    rate limit, or disrupting anything. Meant to be exercised by the test
    suite on every run so selector/namespace drift is caught immediately
    instead of silently no-opping the next time someone actually triggers it.
    """
    if scenario_name not in CHAOS_EXPERIMENTS:
        return {"error": f"Scenario '{scenario_name}' not found."}

    if dry_run:
        matched = _selector_pod_count(CHAOS_EXPERIMENTS[scenario_name]["selector"])
        return {
            "status": "success" if matched > 0 else "warning",
            "dry_run": True,
            "message": (
                f"Dry run: selector would match {matched} pod(s)." if matched > 0
                else "Dry run: selector matched 0 pods — triggering this for real would silently no-op."
            ),
            "matched_pods": matched
        }

    # Check rate limit cooldown period
    now = datetime.now()
    last_trigger = CHAOS_RATE_LIMIT["last_trigger_time"]
    cooldown_minutes = CHAOS_RATE_LIMIT["cooldown_minutes"]

    if last_trigger:
        time_since_last = now - last_trigger
        if time_since_last < timedelta(minutes=cooldown_minutes):
            remaining_seconds = int((timedelta(minutes=cooldown_minutes) - time_since_last).total_seconds())
            return {
                "status": "error",
                "message": f"Rate limit exceeded. Please wait {remaining_seconds} seconds before triggering another chaos scenario.",
                "cooldown_remaining_seconds": remaining_seconds
            }

    # Check maximum concurrent experiments
    if CHAOS_RATE_LIMIT["active_experiments"] >= CHAOS_RATE_LIMIT["max_concurrent"]:
        return {
            "status": "error",
            "message": f"Maximum concurrent chaos experiments ({CHAOS_RATE_LIMIT['max_concurrent']}) reached. Please wait for active experiments to complete.",
            "active_experiments": CHAOS_RATE_LIMIT["active_experiments"]
        }

    scenario = CHAOS_EXPERIMENTS[scenario_name]
    namespace = scenario.get("namespace", "default")
    
    # Create a unique name for the ad-hoc experiment to avoid conflicts
    experiment_name = f"{scenario_name}-{uuid.uuid4().hex[:6]}"
    
    # Construct the PodChaos manifest
    pod_chaos_manifest = {
        "apiVersion": api_version,
        "kind": "PodChaos",
        "metadata": {
            "name": experiment_name,
            "namespace": namespace,
            "labels": {
                "triggered-by": "scenario-runner",
                "original-scenario": scenario_name
            }
        },
        "spec": {
            "action": scenario["action"],
            "mode": scenario["mode"],
            "selector": scenario["selector"],
            "duration": scenario["duration"],
            "gracePeriod": scenario["gracePeriod"]
        }
    }

    try:
        print(f"DEBUG K8S API CALL: Group+Version={api_version}, Namespace={namespace}, Plural={plural}, Name={experiment_name}")

        # Create the custom resource in Kubernetes
        api_client.create_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace=namespace,
            plural=plural,
            body=pod_chaos_manifest,
        )

        # Wait briefly and check if experiment was processed by Chaos Mesh
        import time
        time.sleep(3)  # Give Chaos Mesh time to process

        try:
            # Get the experiment status
            experiment = api_client.get_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace=namespace,
                plural=plural,
                name=experiment_name
            )

            status = experiment.get("status", {})
            conditions = status.get("conditions", [])

            # Check if Chaos Mesh controller processed it
            if not status:
                print(f"WARNING: Experiment created but has no status. Chaos Mesh may not be installed.")
                return {
                    "status": "warning",
                    "message": f"Experiment '{experiment_name}' created but not processed. Check if Chaos Mesh is running."
                }

            # Check if pods were selected
            selected_condition = next((c for c in conditions if c.get("type") == "Selected"), None)
            if selected_condition and selected_condition.get("status") == "False":
                print(f"WARNING: No pods matched the selector")
                return {
                    "status": "warning",
                    "message": f"Experiment '{experiment_name}' created but no pods matched selector."
                }

            print(f"SUCCESS: Experiment processed by Chaos Mesh. Status: {status}")

            # Update rate limit tracking
            CHAOS_RATE_LIMIT["last_trigger_time"] = now
            CHAOS_RATE_LIMIT["active_experiments"] += 1

            return {
                "status": "success",
                "message": f"Successfully triggered '{experiment_name}' and verified execution.",
                "cooldown_minutes": cooldown_minutes
            }

        except ApiException as status_error:
            print(f"WARNING: Could not verify experiment status: {status_error}")

            # Update rate limit tracking (experiment was created)
            CHAOS_RATE_LIMIT["last_trigger_time"] = now
            CHAOS_RATE_LIMIT["active_experiments"] += 1

            return {
                "status": "success",
                "message": f"Experiment '{experiment_name}' created but status verification failed. It may still be running.",
                "cooldown_minutes": cooldown_minutes
            }

    except ApiException as e:
        print(f"Error creating PodChaos object: {e}")
        return {"status": "error", "message": f"Failed to trigger experiment: {e.reason}"}

@app.post("/scenario-runner/api/trigger_stress/dem-memory-leak-45min")
async def trigger_dem_memory_leak_45min():
    """Triggers a 45-minute memory leak scenario that auto-expires (30 min climb + 15 min hold)"""
    import time

    clear_expired_dem_scenario_triggers()

    # Check if already running
    if DEM_FORRESTER_SCENARIOS["memory_leak_trigger_active"]:
        deadline = DEM_FORRESTER_SCENARIOS["memory_leak_trigger_deadline"]
        if deadline and time.time() < deadline:
            remaining = int(deadline - time.time())
            return {
                "status": "error",
                "message": f"DEM memory leak scenario already running. {remaining} seconds remaining."
            }

    # Start the scenario
    duration_sec = DEM_FORRESTER_SCENARIOS["memory_leak_trigger_duration_sec"]
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_active"] = True
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_deadline"] = time.time() + duration_sec

    # Automatically enable payment failure scenarios to show business impact
    PAYMENT_SCENARIOS["card_decline_enabled"] = True
    PAYMENT_SCENARIOS["card_decline_probability"] = 50.0
    PAYMENT_SCENARIOS["gateway_timeout_enabled"] = True
    PAYMENT_SCENARIOS["gateway_timeout_probability"] = 20.0
    PAYMENT_SCENARIOS["gateway_timeout_delay"] = 10.0

    return {
        "status": "success",
        "message": f"Memory leak scenario triggered for {duration_sec // 60} minutes with payment failures. Will auto-expire.",
        "duration_seconds": duration_sec,
        "rate_mb_per_sec": DEM_FORRESTER_SCENARIOS["memory_leak_rate_mb_per_sec"],
        "max_mb": DEM_FORRESTER_SCENARIOS["memory_leak_max_mb"],
        "payment_failures_enabled": True,
        "card_decline_probability": 50.0,
        "gateway_timeout_probability": 20.0
    }

@app.post("/scenario-runner/api/trigger_stress/dem-memory-leak-10min")
async def trigger_dem_memory_leak_10min():
    """Triggers a 25-minute memory leak scenario that auto-expires (10 min climb + 15 min hold)"""
    import time

    clear_expired_dem_scenario_triggers()

    # Check if already running
    if DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_active"]:
        deadline = DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_deadline"]
        if deadline and time.time() < deadline:
            remaining = int(deadline - time.time())
            return {
                "status": "error",
                "message": f"Memory leak scenario already running. {remaining} seconds remaining."
            }

    # Start the scenario
    duration_sec = DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_duration_sec"]
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_active"] = True
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_deadline"] = time.time() + duration_sec

    # Automatically enable payment failure scenarios to show business impact
    PAYMENT_SCENARIOS["card_decline_enabled"] = True
    PAYMENT_SCENARIOS["card_decline_probability"] = 50.0
    PAYMENT_SCENARIOS["gateway_timeout_enabled"] = True
    PAYMENT_SCENARIOS["gateway_timeout_probability"] = 20.0
    PAYMENT_SCENARIOS["gateway_timeout_delay"] = 10.0

    return {
        "status": "success",
        "message": f"Memory leak scenario triggered for {duration_sec // 60} minutes with payment failures. Will auto-expire.",
        "duration_seconds": duration_sec,
        "rate_mb_per_sec": DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_rate"],
        "max_mb": DEM_FORRESTER_SCENARIOS["memory_leak_max_mb"],
        "payment_failures_enabled": True,
        "card_decline_probability": 50.0,
        "gateway_timeout_probability": 20.0
    }

@app.post("/scenario-runner/api/trigger_stress/{scenario_name}")
async def trigger_stress_experiment(scenario_name: str, dry_run: bool = False):
    """Triggers a one-time Stress Chaos experiment with rate limiting.

    dry_run=true checks whether the scenario's selector would match any live
    pods right now — without creating a chaos-mesh resource, consuming the
    rate limit, or disrupting anything. See trigger_chaos_experiment's
    docstring for why this exists.
    """
    if scenario_name not in STRESS_EXPERIMENTS:
        return {"error": f"Stress scenario '{scenario_name}' not found."}

    if dry_run:
        matched = _selector_pod_count(STRESS_EXPERIMENTS[scenario_name]["selector"])
        return {
            "status": "success" if matched > 0 else "warning",
            "dry_run": True,
            "message": (
                f"Dry run: selector would match {matched} pod(s)." if matched > 0
                else "Dry run: selector matched 0 pods — triggering this for real would silently no-op."
            ),
            "matched_pods": matched
        }

    # Check rate limit cooldown period
    now = datetime.now()
    last_trigger = CHAOS_RATE_LIMIT["last_trigger_time"]
    cooldown_minutes = CHAOS_RATE_LIMIT["cooldown_minutes"]

    if last_trigger:
        time_since_last = now - last_trigger
        if time_since_last < timedelta(minutes=cooldown_minutes):
            remaining_seconds = int((timedelta(minutes=cooldown_minutes) - time_since_last).total_seconds())
            return {
                "status": "error",
                "message": f"Rate limit exceeded. Please wait {remaining_seconds} seconds before triggering another chaos scenario.",
                "cooldown_remaining_seconds": remaining_seconds
            }

    # Check maximum concurrent experiments
    if CHAOS_RATE_LIMIT["active_experiments"] >= CHAOS_RATE_LIMIT["max_concurrent"]:
        return {
            "status": "error",
            "message": f"Maximum concurrent chaos experiments ({CHAOS_RATE_LIMIT['max_concurrent']}) reached. Please wait for active experiments to complete.",
            "active_experiments": CHAOS_RATE_LIMIT["active_experiments"]
        }

    scenario = STRESS_EXPERIMENTS[scenario_name]
    namespace = scenario.get("namespace", "default")

    # Create a unique name for the ad-hoc experiment to avoid conflicts
    experiment_name = f"{scenario_name}-{uuid.uuid4().hex[:6]}"

    # Construct the StressChaos manifest
    stress_chaos_manifest = {
        "apiVersion": api_version,
        "kind": "StressChaos",
        "metadata": {
            "name": experiment_name,
            "namespace": namespace,
            "labels": {
                "triggered-by": "scenario-runner",
                "original-scenario": scenario_name
            }
        },
        "spec": {
            "mode": scenario["mode"],
            "selector": scenario["selector"],
            "duration": scenario["duration"],
            "stressors": scenario["stressors"]
        }
    }

    if scenario.get("containerNames"):
        stress_chaos_manifest["spec"]["containerNames"] = scenario["containerNames"]

    try:
        print(f"DEBUG K8S API CALL: Group+Version={api_version}, Namespace={namespace}, Plural={stress_plural}, Name={experiment_name}")

        # Create the custom resource in Kubernetes
        api_client.create_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace=namespace,
            plural=stress_plural,
            body=stress_chaos_manifest,
        )

        # Wait briefly and check if experiment was processed by Chaos Mesh
        import time
        time.sleep(3)  # Give Chaos Mesh time to process

        try:
            # Get the experiment status
            experiment = api_client.get_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace=namespace,
                plural=stress_plural,
                name=experiment_name
            )

            status = experiment.get("status", {})
            conditions = status.get("conditions", [])

            # Check if Chaos Mesh controller processed it
            if not status:
                print(f"WARNING: Stress experiment created but has no status. Chaos Mesh may not be installed.")
                return {
                    "status": "warning",
                    "message": f"Stress experiment '{experiment_name}' created but not processed. Check if Chaos Mesh is running."
                }

            # Check if pods were selected
            selected_condition = next((c for c in conditions if c.get("type") == "Selected"), None)
            if selected_condition and selected_condition.get("status") == "False":
                print(f"WARNING: No pods matched the selector")
                return {
                    "status": "warning",
                    "message": f"Stress experiment '{experiment_name}' created but no pods matched selector."
                }

            print(f"SUCCESS: Stress experiment processed by Chaos Mesh. Status: {status}")

            # Update rate limit tracking
            CHAOS_RATE_LIMIT["last_trigger_time"] = now
            CHAOS_RATE_LIMIT["active_experiments"] += 1

            return {
                "status": "success",
                "message": f"Successfully triggered '{experiment_name}' and verified execution.",
                "cooldown_minutes": cooldown_minutes
            }

        except ApiException as status_error:
            print(f"WARNING: Could not verify stress experiment status: {status_error}")

            # Update rate limit tracking (experiment was created)
            CHAOS_RATE_LIMIT["last_trigger_time"] = now
            CHAOS_RATE_LIMIT["active_experiments"] += 1

            return {
                "status": "success",
                "message": f"Stress experiment '{experiment_name}' created but status verification failed. It may still be running.",
                "cooldown_minutes": cooldown_minutes
            }

    except ApiException as e:
        print(f"Error creating StressChaos object: {e}")
        return {"status": "error", "message": f"Failed to trigger stress experiment: {e.reason}"}


@app.post("/scenario-runner/api/trigger_network/{scenario_name}")
async def trigger_network_experiment(scenario_name: str, dry_run: bool = False):
    """Triggers a one-time NetworkChaos / DNSChaos experiment with rate limiting.

    Same contract as trigger_stress: the experiment is duration-bound and expires on its own
    (there is no stop call), shares the chaos rate limit, and supports dry_run=true to check
    the selector against live pods without creating anything.
    """
    if scenario_name not in NETWORK_EXPERIMENTS:
        return {"error": f"Network scenario '{scenario_name}' not found."}

    scenario = NETWORK_EXPERIMENTS[scenario_name]

    if dry_run:
        matched = _selector_pod_count(scenario["selector"])
        return {
            "status": "success" if matched > 0 else "warning",
            "dry_run": True,
            "message": (
                f"Dry run: selector would match {matched} pod(s)." if matched > 0
                else "Dry run: selector matched 0 pods — triggering this for real would silently no-op."
            ),
            "matched_pods": matched
        }

    now = datetime.now()
    last_trigger = CHAOS_RATE_LIMIT["last_trigger_time"]
    cooldown_minutes = CHAOS_RATE_LIMIT["cooldown_minutes"]
    if last_trigger:
        time_since_last = now - last_trigger
        if time_since_last < timedelta(minutes=cooldown_minutes):
            remaining_seconds = int((timedelta(minutes=cooldown_minutes) - time_since_last).total_seconds())
            return {
                "status": "error",
                "message": f"Rate limit exceeded. Please wait {remaining_seconds} seconds before triggering another chaos scenario.",
                "cooldown_remaining_seconds": remaining_seconds
            }
    if CHAOS_RATE_LIMIT["active_experiments"] >= CHAOS_RATE_LIMIT["max_concurrent"]:
        return {
            "status": "error",
            "message": f"Maximum concurrent chaos experiments ({CHAOS_RATE_LIMIT['max_concurrent']}) reached. Please wait for active experiments to complete.",
            "active_experiments": CHAOS_RATE_LIMIT["active_experiments"]
        }

    namespace = scenario.get("namespace", "default")
    kind = scenario["kind"]
    network_plural = NETWORK_CHAOS_PLURALS[kind]
    experiment_name = f"{scenario_name}-{uuid.uuid4().hex[:6]}"

    manifest = {
        "apiVersion": api_version,
        "kind": kind,
        "metadata": {
            "name": experiment_name,
            "namespace": namespace,
            "labels": {
                "triggered-by": "scenario-runner",
                "original-scenario": scenario_name
            }
        },
        "spec": scenario["spec"]
    }

    try:
        print(f"DEBUG K8S API CALL: Group+Version={api_version}, Namespace={namespace}, Plural={network_plural}, Name={experiment_name}")
        api_client.create_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace=namespace,
            plural=network_plural,
            body=manifest,
        )

        CHAOS_RATE_LIMIT["last_trigger_time"] = now
        CHAOS_RATE_LIMIT["active_experiments"] += 1

        import time
        time.sleep(3)  # Give Chaos Mesh time to process
        try:
            experiment = api_client.get_namespaced_custom_object(
                group="chaos-mesh.org",
                version="v1alpha1",
                namespace=namespace,
                plural=network_plural,
                name=experiment_name
            )
            status = experiment.get("status", {})
            conditions = status.get("conditions", [])
            if not status:
                return {
                    "status": "warning",
                    "message": f"{kind} '{experiment_name}' created but not processed. Check if Chaos Mesh is running"
                               + (" with the DNS server enabled (dnsServer.create=true)." if kind == "DNSChaos" else ".")
                }
            selected = next((c for c in conditions if c.get("type") == "Selected"), None)
            if selected and selected.get("status") == "False":
                return {
                    "status": "warning",
                    "message": f"{kind} '{experiment_name}' created but no pods matched selector."
                }
            return {
                "status": "success",
                "message": f"Successfully triggered '{experiment_name}' and verified execution.",
                "duration": scenario["duration"],
                "cooldown_minutes": cooldown_minutes
            }
        except ApiException as status_error:
            print(f"WARNING: Could not verify {kind} status: {status_error}")
            return {
                "status": "success",
                "message": f"{kind} '{experiment_name}' created but status verification failed. It may still be running.",
                "duration": scenario["duration"],
                "cooldown_minutes": cooldown_minutes
            }

    except ApiException as e:
        print(f"Error creating {kind} object: {e}")
        return {"status": "error", "message": f"Failed to trigger network experiment: {e.reason}"}


@app.get("/scenario-runner/api/chaos-rate-limit-status")
async def get_chaos_rate_limit_status():
    """Get current rate limiting status for chaos scenarios"""
    now = datetime.now()
    last_trigger = CHAOS_RATE_LIMIT["last_trigger_time"]

    if last_trigger:
        time_since_last = now - last_trigger
        cooldown_remaining = timedelta(minutes=CHAOS_RATE_LIMIT["cooldown_minutes"]) - time_since_last
        can_trigger = cooldown_remaining.total_seconds() <= 0
        cooldown_remaining_seconds = max(0, int(cooldown_remaining.total_seconds()))
    else:
        can_trigger = True
        cooldown_remaining_seconds = 0

    return {
        "status": "success",
        "can_trigger_new": can_trigger and CHAOS_RATE_LIMIT["active_experiments"] < CHAOS_RATE_LIMIT["max_concurrent"],
        "cooldown_minutes": CHAOS_RATE_LIMIT["cooldown_minutes"],
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
        "active_experiments": CHAOS_RATE_LIMIT["active_experiments"],
        "max_concurrent": CHAOS_RATE_LIMIT["max_concurrent"],
        "last_trigger_time": last_trigger.isoformat() if last_trigger else None
    }


@app.post("/scenario-runner/api/chaos-rate-limit-reset")
async def reset_chaos_rate_limit():
    """Reset rate limiting counters (admin use)"""
    CHAOS_RATE_LIMIT["last_trigger_time"] = None
    CHAOS_RATE_LIMIT["active_experiments"] = 0

    return {
        "status": "success",
        "message": "Chaos rate limit counters reset"
    }


@app.post("/scenario-runner/api/run_locust/{locustfile_name}")
async def run_locust_test(locustfile_name: str, num_users: int = 1):
    """
    Triggers a Locust load test from the command line.
    
    Note: In a production environment, running this with subprocess is not recommended.
    A better solution would be to create a Kubernetes Job. This method is for
    demonstration and development purposes.
    """
    # Create a list of arguments to pass to Locust's main function
    locust_args = [
        "locust",  # The first argument is the program name itself
        "-f", f"locust/{locustfile_name}",
        "--host", os.environ.get("LOCUST_HOST"),
        "--users", str(num_users),
        "--spawn-rate", "10",
        "--run-time", "1m",
        "--headless"
    ]
    
    # Save the original sys.argv and then replace it with our arguments
    original_argv = sys.argv
    sys.argv = locust_args
    
    # Create a dummy function to replace sys.exit
    def dummy_exit(code=0):
        if code != 0:
            raise RuntimeError(f"Locust exited with non-zero code {code}")
        
    original_exit = sys.exit
    sys.exit = dummy_exit
    
    try:
        # Deferred import: pulling in locust monkey-patches threading via
        # gevent process-wide. Acceptable here because /run_locust is the
        # only flow that actually needs Locust, and once invoked the process
        # is dedicated to that run.
        from locust import main as locust_main
        locust_main.main()
        return {
            "status": "success",
            "message": f"Locust test '{locustfile_name}' started successfully.",
            "output": "Locust output is not captured when run this way."
        }
    except Exception:
        logging.exception(f"Error running Locust test '{locustfile_name}'")
        return {
            "status": "error",
            "message": f"Failed to start Locust test '{locustfile_name}'. See server logs for details.",
            "output": "Locust test failed. See server logs for details."
        }
    finally:
        # Restore sys.argv and sys.exit to their original states
        sys.argv = original_argv
        sys.exit = original_exit

@app.get("/scenario-runner")
async def ok():
    """Root return 200"""
    return "ok"


# ============================================================================
# Payment Scenario Control Endpoints
# ============================================================================

@app.get("/scenario-runner/api/payment-scenarios")
async def get_payment_scenarios():
    """Get current payment scenario configuration"""
    return {
        "status": "success",
        "scenarios": PAYMENT_SCENARIOS
    }


@app.post("/scenario-runner/api/payment-scenarios/gateway-timeout")
async def toggle_gateway_timeout(enabled: bool, probability: float = 15.0, delay: float = 10.0):
    """Enable/disable gateway timeout scenario with probability"""
    if delay < 1 or delay > 60:
        return {"status": "error", "message": "Delay must be between 1 and 60 seconds"}
    if probability < 0 or probability > 100:
        return {"status": "error", "message": "Probability must be between 0 and 100"}

    PAYMENT_SCENARIOS["gateway_timeout_enabled"] = enabled
    PAYMENT_SCENARIOS["gateway_timeout_delay"] = delay
    PAYMENT_SCENARIOS["gateway_timeout_probability"] = probability

    status_msg = "enabled" if enabled else "disabled"
    return {
        "status": "success",
        "message": f"Gateway timeout scenario {status_msg} ({probability}% of requests)",
        "scenarios": PAYMENT_SCENARIOS
    }


@app.post("/scenario-runner/api/payment-scenarios/card-decline")
async def set_card_decline(enabled: bool, probability: float = 20.0):
    """Enable/disable card decline scenario with probability"""
    if probability < 0 or probability > 100:
        return {"status": "error", "message": "Probability must be between 0 and 100"}

    PAYMENT_SCENARIOS["card_decline_enabled"] = enabled
    PAYMENT_SCENARIOS["card_decline_probability"] = probability

    status_msg = "enabled" if enabled else "disabled"
    return {
        "status": "success",
        "message": f"Card decline scenario {status_msg} ({probability}% of requests)",
        "scenarios": PAYMENT_SCENARIOS
    }


@app.post("/scenario-runner/api/payment-scenarios/stolen-card")
async def set_stolen_card(enabled: bool, probability: float = 10.0):
    """Enable/disable stolen card scenario with probability"""
    if probability < 0 or probability > 100:
        return {"status": "error", "message": "Probability must be between 0 and 100"}

    PAYMENT_SCENARIOS["stolen_card_enabled"] = enabled
    PAYMENT_SCENARIOS["stolen_card_probability"] = probability

    status_msg = "enabled" if enabled else "disabled"
    return {
        "status": "success",
        "message": f"Stolen card scenario {status_msg} ({probability}% of requests)",
        "scenarios": PAYMENT_SCENARIOS
    }


@app.post("/scenario-runner/api/payment-scenarios/reset")
async def reset_payment_scenarios():
    """Reset all payment scenarios to default values"""
    PAYMENT_SCENARIOS["gateway_timeout_enabled"] = False
    PAYMENT_SCENARIOS["gateway_timeout_delay"] = 10.0
    PAYMENT_SCENARIOS["gateway_timeout_probability"] = 0.0
    PAYMENT_SCENARIOS["card_decline_enabled"] = False
    PAYMENT_SCENARIOS["card_decline_probability"] = 0.0
    PAYMENT_SCENARIOS["stolen_card_enabled"] = False
    PAYMENT_SCENARIOS["stolen_card_probability"] = 0.0

    return {
        "status": "success",
        "message": "All payment scenarios reset to defaults",
        "scenarios": PAYMENT_SCENARIOS
    }


# ============================================================================
# Risk Assessment Scenario Control Endpoints
# ============================================================================

@app.get("/scenario-runner/api/risk-assessment/config")
async def get_risk_assessment_config():
    """Get current risk assessment agent configuration"""
    return {
        "status": "success",
        "scenarios": RISK_ASSESSMENT_SCENARIOS
    }


@app.post("/scenario-runner/api/risk-assessment/rogue-agent")
async def toggle_rogue_agent(enabled: bool):
    """
    Enable/disable rogue agent scenario.

    When enabled, switches to gpt-4o-mini (extremely stringent, declines most payments).
    When disabled, uses gpt-4o (normal, balanced risk assessment).
    """
    RISK_ASSESSMENT_SCENARIOS["rogue_agent_enabled"] = enabled

    if enabled:
        RISK_ASSESSMENT_SCENARIOS["agent_name"] = "gpt-4o-mini"
        message = "Rogue agent enabled - using gpt-4o-mini (extremely stringent, will decline most payments)"
    else:
        RISK_ASSESSMENT_SCENARIOS["agent_name"] = "gpt-4o"
        message = "Rogue agent disabled - using gpt-4o (normal risk assessment)"

    # Invalidate support service cache so it picks up the change immediately
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            support_service_url = os.getenv("SUPPORT_SERVICE_URL", "http://support-service:5003")
            response = await client.post(f"{support_service_url}/support-service/invalidate-agent-cache")
            response.raise_for_status()
            print("Successfully invalidated support service risk agent cache")
    except Exception as e:
        print(f"Failed to invalidate support service cache: {e}")
        # Continue anyway - cache will expire naturally in 1 second

    # Small delay to ensure cache invalidation propagates before returning
    # This helps prevent race conditions where tests immediately send requests
    await asyncio.sleep(0.1)

    return {
        "status": "success",
        "message": message,
        "scenarios": RISK_ASSESSMENT_SCENARIOS
    }


@app.post("/scenario-runner/api/risk-assessment/reset")
async def reset_risk_assessment_scenarios():
    """Reset risk assessment scenarios to default values"""
    RISK_ASSESSMENT_SCENARIOS["rogue_agent_enabled"] = False
    RISK_ASSESSMENT_SCENARIOS["agent_name"] = "gpt-4o"

    # Invalidate support service cache so it picks up the reset immediately
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            support_service_url = os.getenv("SUPPORT_SERVICE_URL", "http://support-service:5003")
            response = await client.post(f"{support_service_url}/support-service/invalidate-agent-cache")
            response.raise_for_status()
            print("Successfully invalidated support service risk agent cache")
    except Exception as e:
        print(f"Failed to invalidate support service cache: {e}")
        # Continue anyway - cache will expire naturally in 1 second

    # Small delay to ensure cache invalidation propagates before returning
    # This helps prevent race conditions where tests immediately send requests
    await asyncio.sleep(0.1)

    return {
        "status": "success",
        "message": "Risk assessment scenarios reset to defaults (gpt-4o)",
        "scenarios": RISK_ASSESSMENT_SCENARIOS
    }


# ============================================================================
# A/B Testing Scenario Control Endpoints
# ============================================================================

@app.get("/scenario-runner/api/ab-testing/config")
async def get_ab_test_config():
    """Get current A/B testing configuration"""
    return {
        "status": "success",
        "config": AB_TEST_SCENARIOS
    }


@app.post("/scenario-runner/api/ab-testing/lcp-slowness-percentage")
async def toggle_lcp_slowness_percentage(enabled: bool, percentage: float = 50.0, delay_ms: int = 3000):
    """Enable/disable LCP slowness for A/B testing (percentage-based: affects X% of all users)"""
    if percentage < 0 or percentage > 100:
        return {"status": "error", "message": "Percentage must be between 0 and 100"}
    if delay_ms < 0 or delay_ms > 30000:
        return {"status": "error", "message": "Delay must be between 0 and 30000 milliseconds"}

    AB_TEST_SCENARIOS["lcp_slowness_percentage_enabled"] = enabled
    AB_TEST_SCENARIOS["lcp_slowness_percentage"] = percentage
    AB_TEST_SCENARIOS["lcp_slowness_percentage_delay_ms"] = delay_ms

    status_msg = "enabled" if enabled else "disabled"
    return {
        "status": "success",
        "message": f"LCP slowness (percentage) {status_msg} for {percentage}% of users ({delay_ms}ms delay)",
        "config": AB_TEST_SCENARIOS
    }


@app.post("/scenario-runner/api/ab-testing/lcp-slowness-cohort")
async def toggle_lcp_slowness_cohort(enabled: bool, delay_ms: int = 3000):
    """Enable/disable LCP slowness for A/B testing (cohort-based: affects 11 hardcoded test users)"""
    if delay_ms < 0 or delay_ms > 30000:
        return {"status": "error", "message": "Delay must be between 0 and 30000 milliseconds"}

    AB_TEST_SCENARIOS["lcp_slowness_cohort_enabled"] = enabled
    AB_TEST_SCENARIOS["lcp_slowness_cohort_delay_ms"] = delay_ms

    status_msg = "enabled" if enabled else "disabled"
    user_count = AB_TEST_SCENARIOS["lcp_slowness_cohort_user_count"]
    return {
        "status": "success",
        "message": f"LCP slowness (cohort) {status_msg} for {user_count} test users ({delay_ms}ms delay)",
        "config": AB_TEST_SCENARIOS
    }


@app.post("/scenario-runner/api/ab-testing/db-pool-stress")
async def toggle_db_pool_stress(enabled: bool, delay_ms: int = 500, affected_pool: str = "pool-a"):
    """Enable/disable database pool stress scenario (affects users on specific pool)"""
    if delay_ms < 0 or delay_ms > 10000:
        return {"status": "error", "message": "Delay must be between 0 and 10000 milliseconds"}
    if affected_pool not in ["pool-a", "pool-b"]:
        return {"status": "error", "message": "Affected pool must be 'pool-a' or 'pool-b'"}

    AB_TEST_SCENARIOS["db_pool_stress_enabled"] = enabled
    AB_TEST_SCENARIOS["db_pool_stress_delay_ms"] = delay_ms
    AB_TEST_SCENARIOS["db_pool_stress_affected_pool"] = affected_pool

    status_msg = "enabled" if enabled else "disabled"
    return {
        "status": "success",
        "message": f"Database pool stress scenario {status_msg} for {affected_pool} ({delay_ms}ms delay)",
        "config": AB_TEST_SCENARIOS
    }


@app.post("/scenario-runner/api/ab-testing/reset")
async def reset_ab_test_scenarios():
    """Reset all A/B test scenarios to default values"""
    AB_TEST_SCENARIOS["lcp_slowness_percentage_enabled"] = False
    AB_TEST_SCENARIOS["lcp_slowness_percentage"] = 50.0
    AB_TEST_SCENARIOS["lcp_slowness_percentage_delay_ms"] = 3000
    AB_TEST_SCENARIOS["lcp_slowness_cohort_enabled"] = False
    AB_TEST_SCENARIOS["lcp_slowness_cohort_delay_ms"] = 3000
    AB_TEST_SCENARIOS["db_pool_stress_enabled"] = False
    AB_TEST_SCENARIOS["db_pool_stress_delay_ms"] = 500
    AB_TEST_SCENARIOS["db_pool_stress_affected_pool"] = "pool-a"

    return {
        "status": "success",
        "message": "All A/B test scenarios reset to defaults",
        "config": AB_TEST_SCENARIOS
    }


# ============================================================================
# Memory Leak Scenarios
# ============================================================================

def clear_expired_dem_scenario_triggers():
    """Clear _active flags for DEM scenario triggers whose deadline has passed.

    Deadlines alone don't stop a stale trigger from shadowing a newer one:
    accounts_service checks the 10min trigger via `elif` before the 45min
    trigger, so a 10min trigger left active past its own deadline silently
    blocks a later 45min trigger from ever leaking memory.
    """
    now = time.time()

    if DEM_FORRESTER_SCENARIOS["memory_leak_trigger_active"]:
        deadline = DEM_FORRESTER_SCENARIOS["memory_leak_trigger_deadline"]
        if deadline and now >= deadline:
            DEM_FORRESTER_SCENARIOS["memory_leak_trigger_active"] = False
            DEM_FORRESTER_SCENARIOS["memory_leak_trigger_deadline"] = None

    if DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_active"]:
        deadline = DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_deadline"]
        if deadline and now >= deadline:
            DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_active"] = False
            DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_deadline"] = None


@app.get("/scenario-runner/api/dem-memory-leak/config")
async def get_dem_memory_leak_config():
    """Get current memory leak scenario configuration"""
    clear_expired_dem_scenario_triggers()
    return {
        "status": "success",
        "config": DEM_FORRESTER_SCENARIOS
    }


@app.post("/scenario-runner/api/dem-memory-leak/toggle")
async def toggle_dem_memory_leak_manual(enabled: bool, rate_mb_per_sec: int = 10, max_mb: int = 500):
    """Enable/disable memory leak manually (persistent toggle)"""
    if rate_mb_per_sec < 1 or rate_mb_per_sec > 100:
        return {"status": "error", "message": "rate_mb_per_sec must be between 1 and 100"}
    if max_mb < 100 or max_mb > 2000:
        return {"status": "error", "message": "max_mb must be between 100 and 2000"}

    DEM_FORRESTER_SCENARIOS["memory_leak_toggle_enabled"] = enabled
    DEM_FORRESTER_SCENARIOS["memory_leak_rate_mb_per_sec"] = rate_mb_per_sec
    DEM_FORRESTER_SCENARIOS["memory_leak_max_mb"] = max_mb

    status_msg = "enabled" if enabled else "disabled"
    return {
        "status": "success",
        "message": f"Memory leak manual toggle {status_msg} ({rate_mb_per_sec} MB/sec, max {max_mb} MB)",
        "config": DEM_FORRESTER_SCENARIOS
    }


@app.post("/scenario-runner/api/dem-memory-leak/reset")
async def reset_dem_memory_leak_scenarios():
    """Reset all memory leak scenarios AND payment scenarios to default values"""
    DEM_FORRESTER_SCENARIOS["memory_leak_toggle_enabled"] = False
    DEM_FORRESTER_SCENARIOS["memory_leak_rate_mb_per_sec"] = 0.44  # Slow climb (0.44 MB/sec for 30 min)
    DEM_FORRESTER_SCENARIOS["memory_leak_max_mb"] = 800
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_active"] = False
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_deadline"] = None
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_duration_sec"] = 2700  # 45 minutes (30 min climb + 15 min hold)
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_active"] = False
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_deadline"] = None
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_duration_sec"] = 1500  # 25 minutes (10 min climb + 15 min hold)
    DEM_FORRESTER_SCENARIOS["memory_leak_trigger_10min_rate"] = 1.33  # Fast climb (1.33 MB/sec for 10 min)

    # Also reset payment scenarios (auto-enabled during memory leak scenario)
    PAYMENT_SCENARIOS["card_decline_enabled"] = False
    PAYMENT_SCENARIOS["card_decline_probability"] = 0.0
    PAYMENT_SCENARIOS["gateway_timeout_enabled"] = False
    PAYMENT_SCENARIOS["gateway_timeout_probability"] = 0.0

    return {
        "status": "success",
        "message": "Memory leak scenarios and payment scenarios reset to defaults",
        "config": DEM_FORRESTER_SCENARIOS,
        "payment_scenarios_reset": True
    }


# ============================================================================
# db-360: New Relic Query Performance Monitoring demo load
#
# Spawns sustained MSSQL load (spending-velocity SELECT + blocker + contender
# UPDATE) so the NR QPM execution-plan panel populates with rich plans
# (Sort, Window Aggregate, Hash Match). Replaces the manual
# `kubectl exec`-based run-banking-load.sh — these endpoints are HTTP-callable
# from goblin-swarm CI without cluster credentials.
#
# Requires MSSQL with enough memory headroom (MSSQL_MEMORY_LIMIT_MB ~= 6144);
# otherwise queries stall on RESOURCE_SEMAPHORE waits and never produce plans.
# ============================================================================

# Connection string mirrors transaction_service.py (same secret/configmap envs).
DB360_CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={os.getenv('DB_SERVER', '')};"
    f"DATABASE={os.getenv('DB_DATABASE', '')};"
    f"UID={os.getenv('DB_USERNAME', '')};"
    f"PWD={os.getenv('DB_PASSWORD', '')};"
    f"TrustServerCertificate=yes"
)

# Spending-velocity SELECT — window functions over ~500K rows of
# BankTransactions joined to Merchants. Produces Sort + Window Aggregate plan.
# Verbatim from utils/scripts/mssql/loadgen/db-direct/run-banking-load.sh:184.
DB360_VELOCITY_SQL = """
SELECT
    t.TxnID,
    t.AccountID,
    t.MerchantID,
    m.Category,
    m.Region,
    m.RiskTier,
    t.Amount,
    t.TxnDate,
    t.TxnType,
    t.Channel,
    ROW_NUMBER()  OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate)
                                                    AS TxnSeq,
    SUM(t.Amount) OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                                    AS CumulativeSpend,
    AVG(t.Amount) OVER (PARTITION BY t.AccountID ORDER BY t.TxnDate
                        ROWS BETWEEN 99 PRECEDING AND CURRENT ROW)
                                                    AS MovingAvg100,
    RANK()        OVER (PARTITION BY m.Category ORDER BY t.Amount DESC)
                                                    AS GlobalAmountRank
FROM BankTransactions t WITH (INDEX(0))
INNER JOIN Merchants m WITH (INDEX(0)) ON m.MerchantID = t.MerchantID
WHERE t.TxnDate >= DATEADD(MONTH, -6, GETDATE())
ORDER BY t.AccountID, t.TxnDate
OPTION (MAXDOP 1);
"""

# Blocker — holds UPDLOCK on flagged high-risk rows for hold_seconds, then
# commits and repeats. WAITFOR DELAY interval is built per-cycle.
DB360_BLOCKER_SELECT_SQL = """
SELECT TOP 100 t.TxnID, t.AccountID, t.Amount, m.Category, m.RiskTier
FROM BankTransactions t WITH (UPDLOCK, ROWLOCK, HOLDLOCK)
INNER JOIN Merchants m ON m.MerchantID = t.MerchantID
WHERE t.Status = 'Flagged' AND m.RiskTier = 3
ORDER BY t.Amount DESC;
"""
DB360_BLOCKER_UPDATE_SQL = """
UPDATE BankTransactions SET Amount = Amount WHERE TxnID IN (
    SELECT TOP 100 t.TxnID FROM BankTransactions t
    INNER JOIN Merchants m ON m.MerchantID = t.MerchantID
    WHERE t.Status = 'Flagged' AND m.RiskTier = 3 ORDER BY t.Amount DESC
);
"""

# Contender — risk-adjusted recalculation over ~500K rows. Hash join + UPDATE.
# Verbatim from run-banking-load.sh:236.
DB360_CONTENDER_SQL = """
UPDATE t
SET t.Amount = t.Amount * (1.0 + (CAST(m.RiskTier AS DECIMAL(5,4)) * 0.0001))
FROM BankTransactions t WITH (INDEX(0))
INNER JOIN Merchants m WITH (INDEX(0)) ON m.MerchantID = t.MerchantID
WHERE t.TxnDate >= DATEADD(MONTH, -6, GETDATE())
  AND t.Status = 'Approved'
  AND m.IsActive = 1
OPTION (MAXDOP 1);
"""

DB360_STATE: Dict[str, Any] = {
    "running": False,
    "started_at": None,
    "deadline": None,            # time.monotonic() value; workers exit when reached
    "config": {},                # workers, block_hold, max_duration
    "workers": [],               # list of threading.Thread (daemon)
    "stop_event": threading.Event(),
    "stats_lock": threading.Lock(),
    "stats": {
        "velocity_runs": 0,
        "blocker_runs": 0,
        "contender_runs": 0,
        "errors": 0,
        "last_error": None,
    },
}
# Tracked separately so /stop can call .cancel() / .rollback() on the
# blocker's open transaction without rummaging through the worker list.
DB360_BLOCKER_CONN: Optional[Any] = None
DB360_LIFECYCLE_LOCK = threading.Lock()


def _db360_hms(seconds: int) -> str:
    """Format seconds as HH:MM:SS for T-SQL WAITFOR DELAY."""
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def _db360_record_error(exc: Exception) -> None:
    with DB360_STATE["stats_lock"]:
        DB360_STATE["stats"]["errors"] += 1
        DB360_STATE["stats"]["last_error"] = f"{type(exc).__name__}: {exc}"[:300]


def _db360_should_stop() -> bool:
    deadline = DB360_STATE["deadline"]
    if DB360_STATE["stop_event"].is_set():
        return True
    if deadline is not None and time.monotonic() >= deadline:
        return True
    return False


def _db360_velocity_worker() -> None:
    while not _db360_should_stop():
        try:
            with pyodbc.connect(DB360_CONNECTION_STRING, timeout=10) as conn:
                conn.timeout = 60
                conn.execute(DB360_VELOCITY_SQL).fetchall()
            with DB360_STATE["stats_lock"]:
                DB360_STATE["stats"]["velocity_runs"] += 1
        except Exception as exc:
            _db360_record_error(exc)
            # Brief back-off so a misconfigured connection doesn't spin hot.
            DB360_STATE["stop_event"].wait(timeout=2)


def _db360_blocker_worker(hold_seconds: int) -> None:
    global DB360_BLOCKER_CONN
    waitfor_sql = f"WAITFOR DELAY '{_db360_hms(hold_seconds)}';"
    while not _db360_should_stop():
        conn = None
        try:
            conn = pyodbc.connect(DB360_CONNECTION_STRING, autocommit=False, timeout=10)
            conn.timeout = hold_seconds + 30
            DB360_BLOCKER_CONN = conn
            cur = conn.cursor()
            cur.execute(DB360_BLOCKER_SELECT_SQL)
            cur.execute(DB360_BLOCKER_UPDATE_SQL)
            cur.execute(waitfor_sql)
            conn.commit()
            with DB360_STATE["stats_lock"]:
                DB360_STATE["stats"]["blocker_runs"] += 1
        except Exception as exc:
            _db360_record_error(exc)
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            DB360_BLOCKER_CONN = None
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        # Brief gap between blocker cycles, but bail immediately on stop.
        DB360_STATE["stop_event"].wait(timeout=2)


def _db360_contender_worker() -> None:
    while not _db360_should_stop():
        try:
            with pyodbc.connect(DB360_CONNECTION_STRING, autocommit=True, timeout=10) as conn:
                conn.timeout = 60
                conn.execute(DB360_CONTENDER_SQL)
            with DB360_STATE["stats_lock"]:
                DB360_STATE["stats"]["contender_runs"] += 1
        except Exception as exc:
            _db360_record_error(exc)
            DB360_STATE["stop_event"].wait(timeout=2)


def _shutdown_db360() -> None:
    """Idempotent stop: cancel in-flight queries, rollback blocker, join threads.

    Safe to call from request handlers, the FastAPI lifespan shutdown hook, or
    multiple times in a row. Returns within ~10s even if the blocker is mid-WAITFOR.
    """
    global DB360_BLOCKER_CONN
    with DB360_LIFECYCLE_LOCK:
        if not DB360_STATE["running"]:
            return
        DB360_STATE["stop_event"].set()

        # Abort the blocker's currently-running statement so it doesn't sit on
        # UPDLOCK for the remainder of its WAITFOR DELAY.
        blocker_conn = DB360_BLOCKER_CONN
        if blocker_conn is not None:
            try:
                blocker_conn.cancel()
            except Exception:
                pass

        for thread in DB360_STATE["workers"]:
            thread.join(timeout=10)

        DB360_STATE["running"] = False
        DB360_STATE["workers"] = []


def _db360_status_snapshot() -> Dict[str, Any]:
    deadline = DB360_STATE["deadline"]
    seconds_remaining = (
        max(0, int(deadline - time.monotonic())) if deadline is not None else 0
    )
    workers_alive = sum(1 for t in DB360_STATE["workers"] if t.is_alive())
    with DB360_STATE["stats_lock"]:
        stats = dict(DB360_STATE["stats"])
    return {
        "running": DB360_STATE["running"],
        "started_at": DB360_STATE["started_at"],
        "config": DB360_STATE["config"],
        "stats": stats,
        "workers_alive": workers_alive,
        "seconds_remaining": seconds_remaining,
    }


@app.post("/scenario-runner/api/db-360/start")
async def start_db_360(
    workers: int = 4,
    block_hold: int = 120,
    max_duration: int = 1800,
):
    """Spawn N spending-velocity workers + 1 blocker + 1 contender against MSSQL.

    Strict semantics: 409 if already running. Caps protect MSSQL from runaway
    fanout.
    """
    if not (1 <= workers <= 8):
        raise HTTPException(status_code=400, detail="workers must be between 1 and 8")
    if not (10 <= block_hold <= 600):
        raise HTTPException(status_code=400, detail="block_hold must be between 10 and 600 seconds")
    if not (60 <= max_duration <= 3600):
        raise HTTPException(status_code=400, detail="max_duration must be between 60 and 3600 seconds")

    matrix_running = _dbmatrix_any_running()
    if matrix_running:
        raise HTTPException(
            status_code=409,
            detail={"message": f"db-matrix scenario '{matrix_running}' is running; stop it before starting db-360"},
        )

    with DB360_LIFECYCLE_LOCK:
        if DB360_STATE["running"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "db-360 load is already running; call /stop first",
                    "running": True,
                    "started_at": DB360_STATE["started_at"],
                    "config": DB360_STATE["config"],
                },
            )

        DB360_STATE["stop_event"] = threading.Event()
        DB360_STATE["started_at"] = datetime.utcnow().isoformat() + "Z"
        DB360_STATE["deadline"] = time.monotonic() + max_duration
        DB360_STATE["config"] = {
            "workers": workers,
            "block_hold": block_hold,
            "max_duration": max_duration,
        }
        DB360_STATE["stats"] = {
            "velocity_runs": 0,
            "blocker_runs": 0,
            "contender_runs": 0,
            "errors": 0,
            "last_error": None,
        }
        DB360_STATE["workers"] = []

        for i in range(workers):
            t = threading.Thread(
                target=_db360_velocity_worker,
                name=f"db360-velocity-{i}",
                daemon=True,
            )
            t.start()
            DB360_STATE["workers"].append(t)

        blocker = threading.Thread(
            target=_db360_blocker_worker,
            args=(block_hold,),
            name="db360-blocker",
            daemon=True,
        )
        blocker.start()
        DB360_STATE["workers"].append(blocker)

        contender = threading.Thread(
            target=_db360_contender_worker,
            name="db360-contender",
            daemon=True,
        )
        contender.start()
        DB360_STATE["workers"].append(contender)

        DB360_STATE["running"] = True

    return JSONResponse(
        status_code=202,
        content={
            "status": "started",
            "message": (
                f"db-360 load started: {workers} velocity workers + 1 blocker + 1 contender. "
                f"Auto-stops after {max_duration}s."
            ),
            **_db360_status_snapshot(),
        },
    )


@app.post("/scenario-runner/api/db-360/stop")
async def stop_db_360():
    """Cancel in-flight queries, rollback blocker transaction, return stats."""
    was_running = DB360_STATE["running"]
    _shutdown_db360()
    return {
        "status": "stopped",
        "was_running": was_running,
        **_db360_status_snapshot(),
    }


@app.get("/scenario-runner/api/db-360/status")
async def status_db_360():
    """Return current load state, worker counts, and aggregated query stats."""
    return _db360_status_snapshot()


@app.post("/scenario-runner/api/db-360/reset")
async def reset_db_360():
    """Alias for /stop — parity with /payment-scenarios/reset and /risk-assessment/reset."""
    _shutdown_db360()
    return {
        "status": "success",
        "message": "db-360 load stopped and reset",
        **_db360_status_snapshot(),
    }


# ============================================================================
# Database Performance Matrix, acts 2-4 (platform-eng demo scenarios)
#
#   lock-contention  Act 2: hold an exclusive lock on the Ledger table that transaction-service
#                    writes to, so payments stall (K8s 360 stays quiet; only DB 360 sees it).
#   competing-query  Act 3: sustained unindexed analytics scan competing for CPU/IO.
#   plan-regression  Act 4: drop IX_BankTxn_Account and drive an account lookup so the plan flips
#                    from index seek to scan; the index is ALWAYS recreated on stop/expiry/shutdown.
#
# Safety rules (these run against the live demo database):
#   - Every scenario is time-boxed (hard caps below) and cleans up in a `finally`.
#   - One matrix scenario at a time, and none while db-360 is running (db-360's DDL-sensitive
#     scans and blocker would collide with the index drop). db-360/start refuses while one runs.
#   - SET LOCK_TIMEOUT so a collision fails fast with a recorded error instead of hanging.
#   - /db-matrix/reset stops everything and recreates the index even if nothing is running,
#     which is the recovery path if the pod was killed mid plan-regression.
# ============================================================================

DBMATRIX_INDEX_NAME = "IX_BankTxn_Account"

# Locking every Ledger row blocked every payment thread in transaction-service; its health endpoint then
# stopped answering and the kubelet restarted the container ~5 times in 10 min (sandbox, 2026-10-22).
# Payment traffic concentrates on AccountID 1 and 2 (measured), so lock only AccountID 1 and use a short
# default window: about half the payments block, but not enough to exhaust the thread pool.
DBMATRIX_LEDGER_LOCK_ACCOUNT = 1
DBMATRIX_LEDGER_LOCK_SQL = f"UPDATE Ledger SET CurrentBalance = CurrentBalance WHERE AccountID = {DBMATRIX_LEDGER_LOCK_ACCOUNT};"

DBMATRIX_SCAN_SQL = """
SELECT
    m.Category,
    m.Region,
    COUNT(*) AS TxnCount,
    SUM(bt.Amount) AS TotalAmount,
    AVG(bt.Amount) AS AvgAmount,
    CHECKSUM_AGG(CHECKSUM(bt.TxnID, bt.AccountID, bt.Amount)) AS ChkAgg
FROM BankTransactions bt
INNER JOIN Merchants m ON m.MerchantID = bt.MerchantID
WHERE DATEADD(SECOND, 0, bt.TxnDate) >= '2000-01-01'
GROUP BY m.Category, m.Region
ORDER BY TotalAmount DESC;
"""

# One statement per execute() so DB 360's top-query collection sees it as its own batch.
DBMATRIX_LOOKUP_SQL = (
    "SELECT TxnID, AccountID, MerchantID, Amount, TxnDate, TxnType, Status, Channel "
    "FROM BankTransactions WHERE AccountID = 12345 ORDER BY TxnDate DESC;"
)

DBMATRIX_DROP_INDEX_SQL = (
    f"IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = '{DBMATRIX_INDEX_NAME}' "
    f"AND object_id = OBJECT_ID('dbo.BankTransactions')) "
    f"DROP INDEX {DBMATRIX_INDEX_NAME} ON dbo.BankTransactions;"
)
DBMATRIX_CREATE_INDEX_SQL = (
    f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = '{DBMATRIX_INDEX_NAME}' "
    f"AND object_id = OBJECT_ID('dbo.BankTransactions')) "
    f"CREATE INDEX {DBMATRIX_INDEX_NAME} ON dbo.BankTransactions (AccountID);"
)
DBMATRIX_INDEX_PRESENT_SQL = (
    f"SELECT COUNT(*) FROM sys.indexes WHERE name = '{DBMATRIX_INDEX_NAME}' "
    f"AND object_id = OBJECT_ID('dbo.BankTransactions');"
)

# min/default/max are seconds. Caps are deliberate; do not raise without thinking about blast radius.
DBMATRIX_BASELINE_SECONDS = 150  # plan-regression: seconds of lookups with the index in place before the drop.
# The NRDOT top-query collector reports per-scrape deltas (60 s interval), so a plan must survive at least two
# scrapes before New Relic shows it; 45 s was too short (sandbox 2026-10-22), 150 s covers two with margin.

DBMATRIX_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "lock-contention": {"min": 10, "default": 120, "max": 600,
                        "description": "Exclusive lock on Ledger held so payments queue behind it"},
    "competing-query": {"min": 10, "default": 300, "max": 300,
                        "description": "Sustained unindexed analytics scan competing for CPU/IO"},
    "plan-regression": {"min": 10, "default": 420, "max": 600,
                        "description": "Drops IX_BankTxn_Account and drives an account lookup; index restored on stop"},
}

DBMATRIX_LOCK = threading.Lock()
DBMATRIX_STATE: Dict[str, Dict[str, Any]] = {
    name: {
        "running": False, "started_at": None, "deadline": None, "duration": None,
        "stop_event": threading.Event(), "thread": None, "conn": None,
        "stats": {"iterations": 0, "errors": 0, "last_error": None},
        "restore_error": None,
    }
    for name in DBMATRIX_SCENARIOS
}


def _dbmatrix_connect(autocommit: bool):
    return pyodbc.connect(DB360_CONNECTION_STRING, autocommit=autocommit, timeout=10)


def _dbmatrix_record_error(name: str, exc: Exception) -> None:
    st = DBMATRIX_STATE[name]
    st["stats"]["errors"] += 1
    st["stats"]["last_error"] = f"{type(exc).__name__}: {exc}"[:300]


def _dbmatrix_should_stop(name: str) -> bool:
    st = DBMATRIX_STATE[name]
    return st["stop_event"].is_set() or (st["deadline"] is not None and time.monotonic() >= st["deadline"])


def _dbmatrix_index_present() -> Optional[bool]:
    """True/False from the live catalog, or None if the database can't be reached."""
    try:
        with _dbmatrix_connect(autocommit=True) as conn:
            return bool(conn.execute(DBMATRIX_INDEX_PRESENT_SQL).fetchone()[0])
    except Exception:
        return None


def _dbmatrix_restore_index() -> Optional[str]:
    """Idempotently recreate the index. Returns an error string on failure, else None."""
    try:
        with _dbmatrix_connect(autocommit=True) as conn:
            conn.timeout = 300
            conn.execute("SET LOCK_TIMEOUT 60000;")
            conn.execute(DBMATRIX_CREATE_INDEX_SQL)
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"[:300]


def _dbmatrix_worker(name: str) -> None:
    st = DBMATRIX_STATE[name]
    try:
        if name == "lock-contention":
            conn = _dbmatrix_connect(autocommit=False)
            st["conn"] = conn
            try:
                conn.execute("SET LOCK_TIMEOUT 15000;")
                conn.execute(DBMATRIX_LEDGER_LOCK_SQL)       # X locks held until rollback
                st["stats"]["iterations"] = 1
                remaining = max(0.0, st["deadline"] - time.monotonic())
                st["stop_event"].wait(timeout=remaining)
            finally:
                try:
                    conn.rollback()                           # releases the lock; data unchanged
                finally:
                    st["conn"] = None
                    conn.close()

        elif name == "competing-query":
            while not _dbmatrix_should_stop(name):
                try:
                    with _dbmatrix_connect(autocommit=True) as conn:
                        st["conn"] = conn
                        conn.timeout = 60
                        conn.execute("SET LOCK_TIMEOUT 15000;")
                        while not _dbmatrix_should_stop(name):
                            conn.execute(DBMATRIX_SCAN_SQL).fetchall()
                            st["stats"]["iterations"] += 1
                except Exception as exc:
                    if not _dbmatrix_should_stop(name):
                        _dbmatrix_record_error(name, exc)
                        st["stop_event"].wait(timeout=2)
                finally:
                    st["conn"] = None

        elif name == "plan-regression":
            try:
                # Baseline phase: run the lookup once a second WITH the index so monitoring records the
                # index-seek plan before the drop; the later scan then shows up as a plan-hash change.
                baseline_secs = min(DBMATRIX_BASELINE_SECONDS, int(st["duration"] // 3))
                st["stats"]["phase"] = "baseline"
                if baseline_secs > 0:
                    if not _dbmatrix_index_present():
                        _dbmatrix_restore_index()   # a missing index would make the "baseline" a scan too
                    baseline_end = time.monotonic() + baseline_secs
                    try:
                        with _dbmatrix_connect(autocommit=True) as conn:
                            st["conn"] = conn
                            conn.timeout = 30
                            while time.monotonic() < baseline_end and not _dbmatrix_should_stop(name):
                                conn.execute(DBMATRIX_LOOKUP_SQL).fetchall()
                                st["stats"]["baseline_iterations"] += 1
                                st["stop_event"].wait(timeout=1)
                    except Exception as exc:
                        if not _dbmatrix_should_stop(name):
                            _dbmatrix_record_error(name, exc)
                    finally:
                        st["conn"] = None
                st["stats"]["phase"] = "dropping"
                # Other queries may be scanning BankTransactions (they hold shared schema locks), so the
                # exclusive lock DROP INDEX needs may not be free. Retry with a short lock timeout inside the
                # scenario window instead of one long wait: each attempt blocks the table only briefly.
                dropped = False
                while not dropped and not _dbmatrix_should_stop(name):
                    st["stats"]["drop_attempts"] = st["stats"].get("drop_attempts", 0) + 1
                    try:
                        with _dbmatrix_connect(autocommit=True) as conn:
                            st["conn"] = conn
                            conn.timeout = 30
                            conn.execute("SET LOCK_TIMEOUT 5000;")
                            conn.execute(DBMATRIX_DROP_INDEX_SQL)
                        dropped = True
                    except Exception as exc:
                        if _dbmatrix_should_stop(name):
                            break
                        if "1222" in str(exc):
                            st["stats"]["drop_lock_timeouts"] = st["stats"].get("drop_lock_timeouts", 0) + 1
                        else:
                            _dbmatrix_record_error(name, exc)
                        st["stop_event"].wait(timeout=3)
                    finally:
                        st["conn"] = None
                st["stats"]["index_dropped"] = dropped
                if dropped:
                    st["stats"]["phase"] = "regression"
                while dropped and not _dbmatrix_should_stop(name):
                    try:
                        with _dbmatrix_connect(autocommit=True) as conn:
                            st["conn"] = conn
                            conn.timeout = 60
                            while not _dbmatrix_should_stop(name):
                                conn.execute(DBMATRIX_LOOKUP_SQL).fetchall()
                                st["stats"]["iterations"] += 1
                    except Exception as exc:
                        if not _dbmatrix_should_stop(name):
                            _dbmatrix_record_error(name, exc)
                            st["stop_event"].wait(timeout=2)
                    finally:
                        st["conn"] = None
            finally:
                # Always put the index back, whatever happened above.
                st["restore_error"] = _dbmatrix_restore_index()
    except Exception as exc:
        _dbmatrix_record_error(name, exc)
    finally:
        st["running"] = False


def _dbmatrix_any_running() -> Optional[str]:
    for name, st in DBMATRIX_STATE.items():
        if st["running"]:
            return name
    return None


def _dbmatrix_stop(name: str) -> bool:
    """Idempotent. Signals the worker, cancels any in-flight query, waits for cleanup (incl. index restore)."""
    st = DBMATRIX_STATE[name]
    was_running = st["running"]
    st["stop_event"].set()
    conn = st["conn"]
    if conn is not None and name != "lock-contention":
        try:
            conn.cancel()
        except Exception:
            pass
    thread = st["thread"]
    if thread is not None:
        thread.join(timeout=630 if name == "plan-regression" else 15)
    return was_running


def _shutdown_dbmatrix() -> None:
    for name in DBMATRIX_SCENARIOS:
        _dbmatrix_stop(name)
    # If the pod is going away mid plan-regression, the worker's finally already restored the index.


def _dbmatrix_snapshot(name: str) -> Dict[str, Any]:
    st = DBMATRIX_STATE[name]
    deadline = st["deadline"]
    out = {
        "scenario": name,
        "running": st["running"],
        "started_at": st["started_at"],
        "duration_seconds": st["duration"],
        "seconds_remaining": max(0, int(deadline - time.monotonic())) if (st["running"] and deadline) else 0,
        "stats": dict(st["stats"]),
    }
    if name == "plan-regression":
        out["index_present"] = _dbmatrix_index_present()
        out["index_restore_error"] = st["restore_error"]
    return out


@app.post("/scenario-runner/api/db-matrix/reset")
async def reset_db_matrix():
    """Stop every matrix scenario and make sure IX_BankTxn_Account exists (recovery path)."""
    with DBMATRIX_LOCK:
        for name in DBMATRIX_SCENARIOS:
            _dbmatrix_stop(name)
        restore_error = _dbmatrix_restore_index()
    return {
        "status": "success" if restore_error is None else "error",
        "message": "db-matrix scenarios stopped; index ensured" if restore_error is None
                   else f"stopped, but index restore failed: {restore_error}",
        "index_present": _dbmatrix_index_present(),
    }


@app.get("/scenario-runner/api/db-matrix/status")
async def status_db_matrix():
    return {name: _dbmatrix_snapshot(name) for name in DBMATRIX_SCENARIOS}


@app.post("/scenario-runner/api/db-matrix/{scenario}/start")
async def start_db_matrix(scenario: str, duration: Optional[int] = None):
    cfg = DBMATRIX_SCENARIOS.get(scenario)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Unknown db-matrix scenario '{scenario}'")
    duration = cfg["default"] if duration is None else duration
    if not (cfg["min"] <= duration <= cfg["max"]):
        raise HTTPException(status_code=400,
                            detail=f"duration must be between {cfg['min']} and {cfg['max']} seconds")

    with DBMATRIX_LOCK:
        running = _dbmatrix_any_running()
        if running:
            raise HTTPException(status_code=409, detail={
                "message": f"db-matrix scenario '{running}' is already running; call its /stop first",
                "running": running})
        if DB360_STATE["running"]:
            raise HTTPException(status_code=409, detail={
                "message": "db-360 load is running; stop it (POST /db-360/stop) before starting a db-matrix scenario"})
        if scenario == "plan-regression" and _dbmatrix_index_present() is False:
            raise HTTPException(status_code=409, detail={
                "message": f"{DBMATRIX_INDEX_NAME} is already missing; call /db-matrix/reset to restore it first"})

        st = DBMATRIX_STATE[scenario]
        st["stop_event"] = threading.Event()
        st["started_at"] = datetime.utcnow().isoformat() + "Z"
        st["duration"] = duration
        st["deadline"] = time.monotonic() + duration
        st["stats"] = {"iterations": 0, "errors": 0, "last_error": None}
        if scenario == "plan-regression":
            st["stats"].update({"phase": "starting", "baseline_iterations": 0, "drop_attempts": 0,
                                "drop_lock_timeouts": 0, "index_dropped": False})
        st["restore_error"] = None
        st["running"] = True
        st["thread"] = threading.Thread(target=_dbmatrix_worker, args=(scenario,),
                                        name=f"dbmatrix-{scenario}", daemon=True)
        st["thread"].start()

    return {"status": "success", "message": f"db-matrix '{scenario}' started; auto-stops in {duration}s",
            **_dbmatrix_snapshot(scenario)}


@app.post("/scenario-runner/api/db-matrix/{scenario}/stop")
async def stop_db_matrix(scenario: str):
    if scenario not in DBMATRIX_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown db-matrix scenario '{scenario}'")
    with DBMATRIX_LOCK:
        was_running = _dbmatrix_stop(scenario)
    return {"status": "stopped", "was_running": was_running, **_dbmatrix_snapshot(scenario)}


@app.get("/scenario-runner/api/db-matrix/{scenario}/status")
async def status_db_matrix_scenario(scenario: str):
    if scenario not in DBMATRIX_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown db-matrix scenario '{scenario}'")
    return _dbmatrix_snapshot(scenario)


# ============================================================================
# Noisy Neighbour (platform-eng demo scenario)
#
#   noisy-neighbor  A throwaway Deployment + HPA (1-3 replicas, scales on its own CPU) is placed on
#                   bill-pay-service's node so the node saturates and the payment services wait for CPU.
#
# Safety rules (this runs on the node that serves live payments):
#   - Nothing existing is modified; only the object named `noisy-neighbor` is created and removed.
#   - Time-boxed. The runner removes both objects at expiry, /stop, /reset and shutdown; if the runner
#     dies, the burner goes idle at its own deadline and /noisy-neighbor/reset removes it.
#   - Refuses to start without CPU headroom for two replicas, or while a db-matrix scenario or
#     db-360 is running.
# ============================================================================

NN_NAME = "noisy-neighbor"
NN_VICTIM_APP_LABEL = "bill-pay-service"      # burner is placed on this pod's node
NN_CPU_REQUEST_M = 600
NN_CPU_LIMIT_M = 1500
NN_MIN_REPLICAS = 1
NN_MAX_REPLICAS = 3
NN_HPA_TARGET_UTILIZATION = 60
NN_DURATION = {"min": 60, "default": 600, "max": 1800}

NN_LOCK = threading.Lock()
NN_STATE: Dict[str, Any] = {
    "running": False, "started_at": None, "deadline": None, "duration": None,
    "node": None, "stop_event": threading.Event(), "thread": None, "image": None,
}

# Two busy processes (the CPU limit caps them), then idle after the deadline.
NN_BURN_SCRIPT = (
    "import multiprocessing as m, os, time\n"
    "deadline = float(os.environ['NN_DEADLINE_EPOCH'])\n"
    "def burn():\n"
    "    while time.time() < deadline:\n"
    "        pass\n"
    "ps = [m.Process(target=burn) for _ in range(2)]\n"
    "[p.start() for p in ps]\n"
    "[p.join() for p in ps]\n"
    "while True:\n"
    "    time.sleep(3600)\n"
)


def _cpu_to_millicores(quantity: Optional[str]) -> int:
    """Kubernetes CPU quantity ('600m', '2', '0.5') to millicores."""
    if not quantity:
        return 0
    q = str(quantity).strip()
    if q.endswith("m"):
        return int(float(q[:-1]))
    return int(float(q) * 1000)


def _nn_own_image(namespace: str) -> str:
    """The image this scenario-runner pod runs, so the burner needs no new image."""
    override = os.getenv("NOISY_NEIGHBOR_IMAGE")
    if override:
        return override
    pod_name = os.getenv("HOSTNAME")
    pod = client.CoreV1Api().read_namespaced_pod(name=pod_name, namespace=namespace)
    return pod.spec.containers[0].image


def _nn_victim_node(namespace: str) -> str:
    pods = client.CoreV1Api().list_namespaced_pod(
        namespace=namespace, label_selector=f"app={NN_VICTIM_APP_LABEL}", field_selector="status.phase=Running")
    for pod in pods.items:
        if pod.spec.node_name:
            return pod.spec.node_name
    raise HTTPException(status_code=409, detail=f"No running {NN_VICTIM_APP_LABEL} pod found in {namespace}")


def _nn_node_headroom(node_name: str) -> Dict[str, int]:
    """Allocatable vs requested CPU (millicores) on a node."""
    core_v1 = client.CoreV1Api()
    try:
        node = core_v1.read_node(name=node_name)
        pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
    except ApiException as exc:
        raise HTTPException(status_code=503,
                            detail=f"Cannot verify node headroom (need read access to nodes and pods): {exc.reason}")
    allocatable = _cpu_to_millicores(node.status.allocatable.get("cpu"))
    requested = 0
    for pod in pods.items:
        if pod.status.phase in ("Succeeded", "Failed"):
            continue
        for container in pod.spec.containers:
            requests = (container.resources.requests or {}) if container.resources else {}
            requested += _cpu_to_millicores(requests.get("cpu"))
    return {"allocatable_m": allocatable, "requested_m": requested, "free_m": allocatable - requested}


def _nn_manifests(namespace: str, image: str, deadline_epoch: float) -> Dict[str, Any]:
    labels = {"app": NN_NAME, "triggered-by": "scenario-runner", "original-scenario": NN_NAME}
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=NN_NAME, namespace=namespace, labels=labels),
        spec=client.V1DeploymentSpec(
            replicas=NN_MIN_REPLICAS,
            selector=client.V1LabelSelector(match_labels={"app": NN_NAME}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1PodSpec(
                    termination_grace_period_seconds=0,
                    affinity=client.V1Affinity(pod_affinity=client.V1PodAffinity(
                        required_during_scheduling_ignored_during_execution=[client.V1PodAffinityTerm(
                            label_selector=client.V1LabelSelector(match_labels={"app": NN_VICTIM_APP_LABEL}),
                            topology_key="kubernetes.io/hostname")])),
                    containers=[client.V1Container(
                        name="burn", image=image, image_pull_policy="IfNotPresent",
                        command=["python", "-c", NN_BURN_SCRIPT],
                        env=[client.V1EnvVar(name="NN_DEADLINE_EPOCH", value=str(deadline_epoch))],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": f"{NN_CPU_REQUEST_M}m", "memory": "128Mi"},
                            limits={"cpu": f"{NN_CPU_LIMIT_M}m", "memory": "256Mi"}))]))))
    hpa = client.V2HorizontalPodAutoscaler(
        metadata=client.V1ObjectMeta(name=NN_NAME, namespace=namespace, labels=labels),
        spec=client.V2HorizontalPodAutoscalerSpec(
            scale_target_ref=client.V2CrossVersionObjectReference(api_version="apps/v1", kind="Deployment", name=NN_NAME),
            min_replicas=NN_MIN_REPLICAS, max_replicas=NN_MAX_REPLICAS,
            metrics=[client.V2MetricSpec(type="Resource", resource=client.V2ResourceMetricSource(
                name="cpu", target=client.V2MetricTarget(type="Utilization", average_utilization=NN_HPA_TARGET_UTILIZATION)))]))
    return {"deployment": deployment, "hpa": hpa}


def _nn_teardown(namespace: str) -> Dict[str, bool]:
    """Idempotent: removes the HPA first (so it cannot scale the Deployment back), then the Deployment."""
    removed = {"hpa": False, "deployment": False}
    try:
        client.AutoscalingV2Api().delete_namespaced_horizontal_pod_autoscaler(name=NN_NAME, namespace=namespace)
        removed["hpa"] = True
    except ApiException as exc:
        if exc.status != 404:
            raise
    try:
        client.AppsV1Api().delete_namespaced_deployment(
            name=NN_NAME, namespace=namespace, propagation_policy="Background")
        removed["deployment"] = True
    except ApiException as exc:
        if exc.status != 404:
            raise
    return removed


def _nn_exists(namespace: str) -> bool:
    try:
        client.AppsV1Api().read_namespaced_deployment(name=NN_NAME, namespace=namespace)
        return True
    except ApiException as exc:
        if exc.status == 404:
            return False
        raise


def _nn_timer(namespace: str, stop_event: threading.Event, deadline_mono: float) -> None:
    """Waits for expiry or /stop, then removes the burner."""
    stop_event.wait(timeout=max(0.0, deadline_mono - time.monotonic()))
    try:
        NN_STATE["last_removed"] = _nn_teardown(namespace)
    except Exception as exc:  # logged; /noisy-neighbor/reset is the recovery path
        logging.error(f"[noisy-neighbor] teardown failed: {exc}")
    finally:
        NN_STATE["running"] = False


def _nn_snapshot(namespace: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "scenario": NN_NAME,
        "running": NN_STATE["running"],
        "started_at": NN_STATE["started_at"],
        "duration_seconds": NN_STATE["duration"],
        "seconds_remaining": (max(0, int(NN_STATE["deadline"] - time.monotonic()))
                              if NN_STATE["running"] and NN_STATE["deadline"] else 0),
        "node": NN_STATE["node"],
    }
    try:
        out["exists"] = _nn_exists(namespace)
        if out["exists"]:
            dep = client.AppsV1Api().read_namespaced_deployment(name=NN_NAME, namespace=namespace)
            out["replicas"] = {"desired": dep.spec.replicas, "ready": dep.status.ready_replicas or 0}
            try:
                hpa = client.AutoscalingV2Api().read_namespaced_horizontal_pod_autoscaler(name=NN_NAME, namespace=namespace)
                out["hpa"] = {"current_replicas": hpa.status.current_replicas, "desired_replicas": hpa.status.desired_replicas}
            except ApiException:
                out["hpa"] = None
    except ApiException as exc:
        out["exists"] = None
        out["error"] = f"cannot read cluster state: {exc.reason}"
    return out


def _shutdown_noisy_neighbor() -> None:
    """Called on process shutdown: do not leave the burner behind."""
    NN_STATE["stop_event"].set()
    if NN_STATE["running"]:
        try:
            _nn_teardown(get_current_namespace())
        except Exception as exc:
            logging.error(f"[noisy-neighbor] shutdown teardown failed: {exc}")


@app.post("/scenario-runner/api/noisy-neighbor/start")
async def start_noisy_neighbor(duration: Optional[int] = None, dry_run: bool = False):
    duration = NN_DURATION["default"] if duration is None else duration
    if duration < NN_DURATION["min"] or duration > NN_DURATION["max"]:
        raise HTTPException(status_code=400,
                            detail=f"duration must be between {NN_DURATION['min']} and {NN_DURATION['max']} seconds")
    other = _dbmatrix_any_running()
    if other or DB360_STATE.get("running"):
        raise HTTPException(status_code=409,
                            detail=f"'{other or 'db-360'}' is running; stop it before starting noisy-neighbor")
    namespace = get_current_namespace()

    def _prepare():
        node = _nn_victim_node(namespace)
        headroom = _nn_node_headroom(node)
        return node, headroom

    node, headroom = await asyncio.to_thread(_prepare)
    needed = 2 * NN_CPU_REQUEST_M
    plan = {"node": node, "cpu_request_m": NN_CPU_REQUEST_M, "cpu_limit_m": NN_CPU_LIMIT_M,
            "replicas": f"{NN_MIN_REPLICAS}-{NN_MAX_REPLICAS}", "headroom": headroom, "duration_seconds": duration}
    if headroom["free_m"] < needed:
        raise HTTPException(status_code=409,
                            detail=f"Not enough CPU headroom on {node}: {headroom['free_m']}m free, need {needed}m "
                                   f"for two replicas")
    if dry_run:
        return {"status": "success", "dry_run": True, "message": "Dry run: nothing created.", "plan": plan}

    with NN_LOCK:
        if NN_STATE["running"]:
            raise HTTPException(status_code=409, detail="noisy-neighbor is already running")
        if await asyncio.to_thread(_nn_exists, namespace):
            raise HTTPException(status_code=409,
                                detail="A noisy-neighbor Deployment already exists (orphan?); POST /noisy-neighbor/reset first")
        image = await asyncio.to_thread(_nn_own_image, namespace)
        deadline_epoch = time.time() + duration
        manifests = _nn_manifests(namespace, image, deadline_epoch)

        def _create():
            client.AppsV1Api().create_namespaced_deployment(namespace=namespace, body=manifests["deployment"])
            try:
                client.AutoscalingV2Api().create_namespaced_horizontal_pod_autoscaler(namespace=namespace, body=manifests["hpa"])
            except Exception:
                _nn_teardown(namespace)
                raise
        try:
            await asyncio.to_thread(_create)
        except ApiException as exc:
            raise HTTPException(status_code=500,
                                detail=f"Could not create the noisy-neighbor objects ({exc.status} {exc.reason}); "
                                       f"if this is a permissions error, the Terraform role has not been applied")

        NN_STATE.update({"running": True, "started_at": datetime.utcnow().isoformat() + "Z", "duration": duration,
                         "deadline": time.monotonic() + duration, "node": node, "image": image,
                         "stop_event": threading.Event()})
        NN_STATE["thread"] = threading.Thread(
            target=_nn_timer, args=(namespace, NN_STATE["stop_event"], NN_STATE["deadline"]),
            name="noisy-neighbor-timer", daemon=True)
        NN_STATE["thread"].start()

    return {"status": "success", "message": f"noisy-neighbor started on {node}; auto-stops in {duration}s",
            "plan": plan, **_nn_snapshot(namespace)}


@app.post("/scenario-runner/api/noisy-neighbor/stop")
async def stop_noisy_neighbor():
    namespace = get_current_namespace()
    was_running = NN_STATE["running"]
    NN_STATE["stop_event"].set()
    thread = NN_STATE["thread"]
    if thread is not None:
        await asyncio.to_thread(thread.join, 30)
    removed = await asyncio.to_thread(_nn_teardown, namespace)
    earlier = NN_STATE.pop("last_removed", None) or {}   # the timer thread may have removed them first
    removed = {k: bool(removed.get(k) or earlier.get(k)) for k in ("hpa", "deployment")}
    NN_STATE["running"] = False
    return {"status": "stopped", "was_running": was_running, "removed": removed, **_nn_snapshot(namespace)}


@app.post("/scenario-runner/api/noisy-neighbor/reset")
async def reset_noisy_neighbor():
    """Recovery: removes the burner even if this runner lost track of it (for example after a restart)."""
    namespace = get_current_namespace()
    NN_STATE["stop_event"].set()
    removed = await asyncio.to_thread(_nn_teardown, namespace)
    NN_STATE["running"] = False
    return {"status": "reset", "removed": removed, **_nn_snapshot(namespace)}


@app.get("/scenario-runner/api/noisy-neighbor/status")
async def status_noisy_neighbor():
    return await asyncio.to_thread(_nn_snapshot, get_current_namespace())

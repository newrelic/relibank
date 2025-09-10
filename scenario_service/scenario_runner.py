import os
import uuid
import yaml
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Dict, Any, List

# Initialize FastAPI app
app = FastAPI(title="Chaos Mesh Scenario Runner")

# Dictionary to store parsed Chaos Mesh experiments
CHAOS_EXPERIMENTS: Dict[str, Dict[str, Any]] = {}

def load_chaos_experiments(yaml_file_path: str):
    """
    Loads chaos experiment definitions from a multi-document YAML file.
    """
    try:
        with open(yaml_file_path, 'r') as file:
            # Use yaml.safe_load_all to parse the multi-document YAML file
            for doc in yaml.safe_load_all(file):
                if doc and doc.get("kind") == "Schedule" and doc.get("spec", {}).get("type") == "PodChaos":
                    name = doc["metadata"]["name"]
                    spec_schedule = doc["spec"]["schedule"]
                    description = doc["metadata"].get("labels", {}).get("target-flow", "No description available.")
                    
                    # Construct a new experiment dictionary for ad-hoc execution
                    CHAOS_EXPERIMENTS[name] = {
                        "namespace": doc["metadata"]["namespace"],
                        "action": spec_schedule["action"],
                        "mode": spec_schedule["mode"],
                        "selector": spec_schedule["selector"],
                        "duration": spec_schedule["duration"],
                        "gracePeriod": spec_schedule["gracePeriod"],
                        "description": description
                    }
    except FileNotFoundError:
        print(f"Error: The YAML file '{yaml_file_path}' was not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")

# Load the experiments at application startup
load_chaos_experiments("relibank/chaos_mesh/experiments/relibank-pod-chaos-examples.yaml")

# Load Kubernetes configuration from the cluster
# This expects the app to be running inside a Kubernetes pod with proper RBAC
try:
    config.load_incluster_config()
except config.ConfigException:
    print("Warning: Could not load in-cluster config. Loading kube config from default location.")
    config.load_kube_config()

# Kubernetes API clients for custom resources
api_client = client.CustomObjectsApi()
api_version = "chaos-mesh.org/v1alpha1"
plural = "podchaos"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page."""
    with open("index.html", "r") as f:
        return f.read()

@app.get("/api/scenarios", response_model=List[Dict[str, Any]])
async def get_scenarios():
    """Returns a list of available chaos scenarios and their details."""
    scenarios_list = []
    for name, details in CHAOS_EXPERIMENTS.items():
        scenarios_list.append({
            "name": name,
            "description": details["description"],
            "type": "chaos-mesh"
        })
    # Placeholder for future Locust scenarios
    scenarios_list.append({
        "name": "pay_cancel.py",
        "description": "Bill pay and cancel with a POST request.",
        "type": "locust"
    })
    return scenarios_list

@app.post("/api/trigger_chaos/{scenario_name}")
async def trigger_chaos_experiment(scenario_name: str):
    """Triggers a one-time Chaos Mesh experiment."""
    if scenario_name not in CHAOS_EXPERIMENTS:
        return {"error": f"Scenario '{scenario_name}' not found."}

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
        # Create the custom resource in Kubernetes
        api_client.create_namespaced_custom_object(
            group="chaos-mesh.org",
            version="v1alpha1",
            namespace=namespace,
            plural=plural,
            body=pod_chaos_manifest,
        )
        return {"status": "success", "message": f"Successfully triggered '{experiment_name}'."}
    except ApiException as e:
        print(f"Error creating PodChaos object: {e}")
        return {"status": "error", "message": f"Failed to trigger experiment: {e.reason}"}

@app.post("/api/run_locust/{locustfile_name}")
async def run_locust_test(locustfile_name: str, num_users: int = 1):
    """
    Triggers a Locust load test from the command line.
    
    Note: In a production environment, running this with subprocess is not recommended.
    A better solution would be to create a Kubernetes Job. This method is for
    demonstration and development purposes.
    """
    locust_command = [
        "locust",
        "-f", f"locust/{locustfile_name}",
        "--host", "http://localhost",  # Base URL can be configured here if needed
        "--users", str(num_users),
        "--spawn-rate", "10",
        "--run-time", "1m",
        "--headless"  # Run in headless mode without the web UI
    ]

    try:
        # Run the command and capture output
        result = subprocess.run(locust_command, capture_output=True, text=True, check=True)
        return {
            "status": "success",
            "message": f"Locust test '{locustfile_name}' started successfully.",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        print(f"Error running Locust: {e}")
        return {
            "status": "error",
            "message": f"Failed to start Locust test: {e.stderr}",
            "output": e.stderr
        }
    
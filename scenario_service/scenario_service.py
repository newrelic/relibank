from locust import main as locust_main
import os
import uuid
import yaml
from pathlib import Path 
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from contextlib import asynccontextmanager

# Dictionary to store parsed Chaos Mesh experiments
CHAOS_EXPERIMENTS: Dict[str, Dict[str, Any]] = {}

# Kubernetes API clients for custom resources
api_client = None
api_version = "chaos-mesh.org/v1alpha1"
plural = "podchaos"

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

# Define the lifespan of the application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Loads chaos experiment definitions on application startup and initializes Kubernetes client.
    """
    global api_client

    base_dir = Path(__file__).parent.absolute()
    yaml_file_path = base_dir / "chaos_mesh" / "experiments" / "relibank-pod-chaos-adhoc.yaml"

    # Define the path to the chaos experiment YAML file
    # yaml_file_path = "chaos_mesh/experiments/relibank-pod-chaos-adhoc.yaml"

    loaded_count = 0 # Initialize counter for successful loads
    # Load and parse the chaos experiment YAML file
    try:
        print(f"INFO: Attempting to read YAML from absolute path: {yaml_file_path}") # Log the resolved path
        
        with open(yaml_file_path, 'r') as file: 
            # Use safe_load_all for multi-document YAML
            for i, doc in enumerate(yaml.safe_load_all(file)):
                if doc:
                    current_kind = doc.get('kind', 'N/A')
                    current_name = doc.get('metadata', {}).get('name', 'N/A')
                    print(f"DEBUG: Parsed document {i}. Kind: {current_kind}, Name: {current_name}")

                    if current_kind == "PodChaos":
                        name = doc["metadata"]["name"]
                        description = doc["metadata"].get("labels", {}).get("target-flow", "No description available.")
                        
                        # Store the complete experiment spec for ad-hoc execution
                        CHAOS_EXPERIMENTS[name] = {
                            "namespace": doc["metadata"]["namespace"],
                            "action": doc["spec"]["action"],
                            "mode": doc["spec"]["mode"],
                            "selector": doc["spec"]["selector"],
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
        print(f"Error: The YAML file was not found at '{yaml_file_path}'. This indicates a Dockerfile COPY issue.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}. Check YAML format.")

    # Initialize Kubernetes client from within the pod
    try:
        config.load_incluster_config()
    except config.ConfigException:
        print("Warning: Could not load in-cluster config. Loading kube config from default location.")
        config.load_kube_config()
    
    api_client = client.CustomObjectsApi()
    
    print("Chaos experiments loaded successfully on startup.")
    yield
    print("Application is shutting down.")

# Initialize FastAPI app with the lifespan
app = FastAPI(title="Relibank Scenario Runner", lifespan=lifespan)

@app.get("/scenario-runner/home", response_class=HTMLResponse)
async def read_root():
    """Serves the main HTML page."""
    with open("index.html", "r") as f:
        return f.read()

@app.get("/scenario-runner/api/scenarios", response_model=List[Dict[str, Any]])
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
    return scenarios_list

@app.post("/scenario-runner/api/trigger_chaos/{scenario_name}")
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
            return {"status": "success", "message": f"Successfully triggered '{experiment_name}' and verified execution."}

        except ApiException as status_error:
            print(f"WARNING: Could not verify experiment status: {status_error}")
            return {
                "status": "success",
                "message": f"Experiment '{experiment_name}' created but status verification failed. It may still be running."
            }

    except ApiException as e:
        print(f"Error creating PodChaos object: {e}")
        return {"status": "error", "message": f"Failed to trigger experiment: {e.reason}"}

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
        locust_main.main()
        return {
            "status": "success",
            "message": f"Locust test '{locustfile_name}' started successfully.",
            "output": "Locust output is not captured when run this way."
        }
    except Exception as e:
        print(f"Error running Locust: {e}")
        return {
            "status": "error",
            "message": f"Failed to start Locust test: {e}",
            "output": str(e)
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

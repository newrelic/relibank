# Scenario Runner Service

The Scenario Runner Service is a Python-based FastAPI application designed to help test the resilience of the Relibank microservice architecture. It provides a web-based UI and a REST API to trigger chaos experiments and run load tests against various services within the Kubernetes cluster.

---

### 🚀 Key Features

* **Chaos Mesh Integration**: Trigger one-time `PodChaos` experiments to test the resilience of individual microservices.

* **Locust Integration**: Run ad-hoc load tests to simulate user traffic and evaluate service performance under stress.

* **Centralized Control**: A single, simple UI to manage and execute chaos and load testing scenarios.

* **Containerized**: The service is packaged in a Docker container for easy deployment in a Kubernetes environment.

---

### ⚙️ Getting Started

To get the Scenario Runner Service up and running, you must deploy it to your Kubernetes cluster using Skaffold.

1.  **Ensure your dependencies are up to date**:
    The service uses a `requirements.txt` file to manage Python dependencies.

2.  **Run Skaffold**:
    Execute the `skaffold dev` command from your project's root directory. This command builds the Docker image, deploys the Kubernetes resources, and sets up port forwarding.

    ```bash
    skaffold dev --default-repo=localhost:5000 --cache-artifacts=false
    ```

3.  **Access the UI**:
    Once the deployment is complete, Skaffold will set up a port forward. You can access the Scenario Runner UI at the following URL:

    ```bash
    http://localhost:8000
    ```

---

### ⚙️ Adding Additional Scenarios

**Locust**:
- Scenarios live here -> relibank/scenario_service/locust
- Locust profiles should have their own file

**Chaos Mesh**:
- Scenarios live here -> relibank/scenario_service/chaos_mesh/experiments/relibank-pod-chaos-adhoc.yaml
- The buttons are populated based on the contents of this file, so add new experiments and rebuild in skaffold to test via the button in the UI
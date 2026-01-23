# Scenario Runner Service

The Scenario Runner Service is a Python-based FastAPI application designed to help test the resilience of the Relibank microservice architecture. It provides a web-based UI and a REST API to trigger chaos experiments and run load tests against various services within the Kubernetes cluster.

---

### 🚀 Key Features

* **Chaos Mesh Integration**: Trigger one-time `PodChaos` and `StressChaos` experiments to test the resilience of individual microservices.

* **Stress Testing**: Inject CPU, memory, and I/O stress into services to validate performance under load.

* **Payment Scenarios**: Toggle payment failure scenarios (gateway timeout, card decline, stolen card) with configurable probabilities.

* **Locust Integration**: Run ad-hoc load tests to simulate user traffic and evaluate service performance under stress.

* **Rate Limiting**: Built-in abuse prevention with cooldown periods (1 min local, 5 min production) and concurrent experiment limits.

* **Centralized Control**: A single, simple UI to manage and execute chaos, stress, and load testing scenarios.

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

**Locust Load Tests**:
- Scenarios live here: `relibank/scenario_service/locust`
- Each Locust profile should have its own file

**Pod Chaos Experiments**:
- Scenarios live here: `relibank/scenario_service/chaos_mesh/experiments/relibank-pod-chaos-adhoc.yaml`
- Add new pod chaos experiments to this file and rebuild with Skaffold

**Stress Chaos Experiments**:
- Scenarios live here: `relibank/scenario_service/chaos_mesh/experiments/relibank-stress-scenarios.yaml`
- Add new stress experiments (CPU, memory, I/O) to this file and rebuild with Skaffold

**Payment Scenarios**:
- Configured via API endpoints in `scenario_service.py`
- Toggle via UI or REST API (`/api/payment-scenarios/*`)

The UI buttons are automatically populated based on the contents of these files, so add new experiments and rebuild in Skaffold to see them in the dashboard.

### 🛡️ Rate Limiting

Rate limiting prevents abuse of chaos experiments:
- **Cooldown**: 1 minute locally, 5 minutes in production (auto-detected)
- **Concurrent limit**: Maximum 3 chaos experiments running simultaneously
- **Applies to**: Both pod chaos and stress chaos experiments
- **Check status**: `GET /api/chaos-rate-limit-status`
- **Reset (admin)**: `POST /api/chaos-rate-limit-reset`
# Relibank AI Support Service

This service provides the conversational AI experience for the Relibank application. It is built
with Python and FastAPI, and uses a **LangGraph multi-agent workflow** (coordinator + specialist
agents) on top of **Azure OpenAI** to hold context-aware support conversations. It also exposes
the AI payment-risk-assessment endpoint used by `bill-pay-service` before a payment is processed.

---

### 🚀 Key Features

* **LangGraph Multi-Agent Workflow**: A coordinator agent routes conversation turns to a
  specialist agent as graph nodes (built with `AzureChatOpenAI` / `create_agent`) — not the OpenAI
  Assistants API.
* **Azure OpenAI Integration**: Connects to an Azure OpenAI deployment via
  `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY`, injected at runtime through a Kubernetes
  Secret (no `.env` file).
* **Payment Risk Assessment**: Exposes an endpoint that evaluates payment transactions for risk
  before `bill-pay-service` processes them, using the same Azure OpenAI models. The active
  risk-assessment model is configurable via the scenario service — see
  [`risk_assessment_service/README.md`](../risk_assessment_service/README.md#-rogue-deployment-demo)
  for the full toggle/behavior reference.
* **Docker Containerization**: Packaged in a lightweight Docker container for deployment alongside
  the rest of the Relibank microservices.
* **Asynchronous Processing**: Built on FastAPI's async capabilities to handle multiple chat
  requests concurrently without blocking.

---

### 📦 API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/support-service/chat` | `POST` | Legacy chat endpoint — routes internally to `/support-service/assistant/chat`. Kept for backward compatibility; new integrations should call the assistant endpoint directly. |
| `/support-service/assistant/chat` | `POST` | Sends a message through the LangGraph coordinator + specialist workflow and returns the generated response. |
| `/support-service/assess-payment-risk` | `POST` | Evaluates a payment transaction for risk using an Azure OpenAI model and returns an approve/decline assessment. |
| `/support-service/invalidate-agent-cache` | `POST` | Forces a refresh of the cached risk-assessment agent configuration read from the scenario service. |
| `/support-service/` | `GET` | Service info. |
| `/support-service/health` | `GET` | Health check endpoint — returns a status of `healthy`. |

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and
Kubernetes.

1. **Ensure Prerequisites**: Docker Desktop (with Kubernetes enabled) or Minikube, Skaffold,
   kubectl, and Helm.

2. **Configure Environment**: From the root of the `relibank` repository, populate `skaffold.env`
   with the required secrets and configuration values, including `AZURE_OPENAI_ENDPOINT` and
   `AZURE_OPENAI_API_KEY`.

3. **Start the Stack**: Run the following command from the root directory to build all images and
   deploy all services to your local Kubernetes cluster:

    ```bash
    skaffold dev
    ```

    This will build the service images, deploy all Kubernetes resources, and set up port
    forwarding automatically.

4. **Test the Service**: Once deployed, send a `POST` request to
   `http://localhost:5003/support-service/assistant/chat` to get a response from the AI assistant.

5. **Debug**:

    ```bash
    kubectl logs -n relibank deployment/support-service --tail=50 -f
    ```

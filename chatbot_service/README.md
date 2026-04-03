# Relibank AI Chatbot Service

This service provides a conversational AI experience for the Relibank application, acting as a conversational AI assistant. It is built using Python with the FastAPI framework and integrates with the OpenAI API for its large language model (LLM) capabilities.

---

### 🚀 Key Features

* **LLM Integration**: Connects to the OpenAI API using a robust asynchronous client. It uses a modern chat completion model (`gpt-4o`) to provide intelligent and context-aware responses.
* **Docker Containerization**: The service is packaged in a lightweight Docker container, making it easy to deploy, scale, and integrate with the rest of the Relibank microservices architecture.
* **Secure Credential Management**: It uses a `.env` file to securely manage the `OPENAI_API_KEY`, ensuring that sensitive credentials are not exposed in the codebase or the final container image.
* **Asynchronous Processing**: The service is built with FastAPI's asynchronous capabilities, allowing it to handle multiple chat requests concurrently without blocking.

---

### 📦 API Endpoints

The service exposes the following API endpoint for interacting with the AI model.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/chat` | `POST` | Sends a prompt to the AI assistant and returns a generated response. |
| `/health` | `GET` | A health check endpoint that returns a status of `healthy`. |

---

### ⚙️ How to Run

This service is deployed as part of the larger **Relibank** application stack using Skaffold and Kubernetes.

1. **Ensure Prerequisites**: Make sure you have Docker Desktop (with Kubernetes enabled) or Minikube, Skaffold, kubectl, and Helm installed.

2. **Configure Environment**: From the root of the `relibank` repository, populate `skaffold.env` with the required secrets and configuration values, including the `OPENAI_API_KEY`.

3. **Start the Stack**: Run the following command from the root directory to build all images and deploy all services to your local Kubernetes cluster:

    ```bash
    skaffold dev
    ```

    This will build the service images, deploy all Kubernetes resources, and set up port forwarding automatically.

4. **Test the Service**: Once deployed, send a `POST` request to `http://localhost:5003/chat` to get a response from the AI assistant.
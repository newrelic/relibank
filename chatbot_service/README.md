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

This service is designed to be run using Docker Compose as part of the larger Relibank application stack.

1.  **Create a `.env` file**: In the root directory of your project (the same location as the `docker-compose.yml` file), create a new file named `.env` and add your OpenAI API key to it.

    ```
    OPENAI_API_KEY=YOUR_API_KEY_HERE
    ```

2.  **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

3.  **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository.

4.  **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

    ```bash
    docker compose up --build
    ```

5.  **Test the Service**: Once the containers are running, send a `POST` request to `http://localhost:5003/chat` to get a response from the AI assistant.
```eof
```
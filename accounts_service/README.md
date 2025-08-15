# Relibank Accounts Service

This service is a core component of the **Relibank** FinServ application. It acts as a dedicated microservice for managing user and account data, using a **PostgreSQL** database as its backend. This service is designed to be highly secure and reliable, providing an API for user and account management.

---

### 🚀 Key Features

* **RESTful API**: Exposes a RESTful API for managing user accounts, checking accounts, savings accounts, and credit accounts.

* **PostgreSQL Database**: The service is tightly integrated with a PostgreSQL database, ensuring all account and user data is consistently and reliably stored.

* **Data Validation**: It uses Pydantic models to validate incoming API requests and ensure the data conforms to the required schema before being processed.

---

### 📦 API Endpoints

The service exposes the following API endpoints, which are designed to be consumed by other microservices or the customer portal.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/users` | `POST` | Creates a new user account in the database. |
| `/users/{user_id}` | `GET` | Retrieves a single user's information by their unique ID. |
| `/accounts/{user_id}` | `GET` | Retrieves all accounts (checking, savings, and credit) associated with a specific user. |
| `/accounts/{user_id}` | `POST` | Creates a new account (checking, savings, or credit) and links it to a user. |
| `/health` | `GET` | A health check endpoint that returns a status of `healthy`. |

---

### ⚙️ How to Run

This service is designed to be run using Docker Compose as part of the larger **Relibank** application stack.

1.  **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

2.  **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository, where the `docker-compose.yml` file is located.

3.  **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

    ```bash
    docker compose up --build
    ```

    This command will start the `accounts-db` and other dependent containers, wait for them to become healthy, and then start the `accounts-service`.

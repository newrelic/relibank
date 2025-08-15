# Relibank Bill Pay Service

This service is a core component of the **Relibank** FinServ application. Its primary function is to handle customer-initiated payment requests and cancellations. It acts as a **producer** in our event-driven architecture, validating requests and publishing events to a **Kafka** message queue for other services to consume.

---

### 🚀 Key Features

* **RESTful API**: Exposes a RESTful API for handling one-time, recurring, and cancellation requests.

* **Pydantic Validation**: Validates all incoming API requests to ensure data integrity.

* **Kafka Producer**: Publishes payment-related events to dedicated Kafka topics: `bill_payments`, `recurring_payments`, and `payment_cancellations`.

* **Service-to-Service Communication**: Makes a synchronous API call to the `transaction-service` to check for the existence of a `billId` before processing a payment or cancellation. This ensures data consistency and prevents duplicate transactions.

* **Asynchronous Processing**: All payments are handled asynchronously by publishing events, allowing for a highly responsive user experience.

---

### 📦 API Endpoints

The service exposes the following API endpoints, which are designed to be consumed by the customer portal or other upstream services.

| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/pay` | `POST` | Initiates a one-time bill payment. | `fromAccountId`, `toAccountId`, `amount`, `currency`, `billId` |
| `/recurring` | `POST` | Schedules a recurring bill payment. | `fromAccountId`, `toAccountId`, `amount`, `currency`, `billId`, `frequency`, `startDate` |
| `/cancel/{bill_id}` | `POST` | Cancels a pending or recurring payment after verifying it exists. | `user_id` |
| `/health` | `GET` | A health check endpoint that returns a status of `healthy`. | None |

---

### ⚙️ How to Run

This service is designed to be run using Docker Compose as part of the larger **Relibank** application stack.

1.  **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

2.  **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository, where the `docker-compose.yml` file is located.

3.  **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

    ```bash
    docker compose up --build
    ```

    This command will start the `mssql` and `kafka` containers first, wait for them to become healthy, and then start the `bill-pay` service.

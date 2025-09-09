# Relibank Event Scheduler Service

This service is a crucial component of the **Relibank** event-driven architecture, designed to act as a scheduler and trigger events for recurring payments. It reads payment schedules from the **MSSQL** database and publishes events to the **Kafka** message queue at the appropriate time.

---

### 🚀 Key Features

* **Database-Driven Scheduling**: The service connects to the MSSQL database to retrieve recurring payment schedules, ensuring it's always working with the system of record.

* **Time-Based Logic**: A background loop periodically checks for payments that are due on the current day.

* **Kafka Producer**: When a recurring payment is due, the service publishes a `PaymentDueNotificationEvent` to a dedicated Kafka topic.

* **Asynchronous Processing**: The scheduler is decoupled from the services that consume its events, allowing them to scale independently.

---

### 📦 Data Flow

The scheduler service works with the following data sources:

* **Database**: It queries the `Transactions` table in the MSSQL database to find all records with an `EventType` of `RecurringPaymentScheduled`.

* **Kafka Topics**: It publishes a `PaymentDueNotificationEvent` to the `payment_due_notifications` topic. The `notifications-service` and `transaction-service` consume this event to trigger a notification and process the payment, respectively.

---

### ⚙️ How to Run

This service is designed to be run using Docker Compose as part of the larger **Relibank** application stack.

1.  **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

2.  **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository, where the `docker-compose.yml` file is located.

3.  **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

    ```bash
    docker compose up --build
    ```

    This command will start the `mssql` and `kafka` containers first, wait for them to become healthy, and then start the `scheduler-service` and other services.

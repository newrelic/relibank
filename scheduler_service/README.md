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

This service is deployed as part of the larger **Relibank** application stack using Skaffold and Kubernetes.

1. **Ensure Prerequisites**: Make sure you have Docker Desktop (with Kubernetes enabled) or Minikube, Skaffold, kubectl, and Helm installed.

2. **Configure Environment**: From the root of the `relibank` repository, populate `skaffold.env` with the required secrets and configuration values.

3. **Start the Stack**: Run the following command from the root directory to build all images and deploy all services to your local Kubernetes cluster:

    ```bash
    skaffold dev
    ```

    This will build the service images, deploy all Kubernetes resources, and set up port forwarding automatically.

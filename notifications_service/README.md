# Relibank Notifications Service

This service is a crucial component of the **Relibank** event-driven architecture, designed to provide real-time updates to users via email and SMS. It acts as a dedicated **consumer**, reacting to a variety of payment-related events published to the **Kafka** message queue.

---

### 🚀 Key Features

* **Event-Driven**: The service is entirely asynchronous and decoupled from other services. It doesn't initiate actions itself but instead reacts to events from the `bill-pay` and `scheduler-service`.

* **Multi-Channel Notifications**: It contains draft functionality for sending notifications via email and SMS. The code is structured to support different providers, with commented-out examples for popular services like **Twilio** and **SendGrid**, as well as Azure-native **Azure Communication Services (ACS)**.

* **Pydantic Validation**: It uses Pydantic to validate incoming Kafka messages against a predefined schema, ensuring that the event data is clean and correctly formatted before a notification is sent.

---

### 📦 Event Topics

The service is configured to consume events from the following Kafka topics:

| Topic | Description | 
 | ----- | ----- | 
| `bill_payments` | Notifies users when a one-time payment has been successfully initiated. | 
| `recurring_payments` | Notifies users when a new recurring payment has been scheduled. | 
| `payment_cancellations` | Notifies users when a payment has been successfully canceled. | 
| `payment_due_notifications` | Notifies users that a recurring payment is coming up and is now due. | 

---

### ⚙️ How to Run

This service is designed to be run using Docker Compose as part of the larger **Relibank** application stack.

1. **Ensure Docker Compose is Installed**: Make sure you have Docker and Docker Compose installed and running on your system.

2. **Navigate to the Root Directory**: Open a terminal and navigate to the root directory of the `relibank` repository, where the `docker-compose.yml` file is located.

3. **Start the Stack**: Run the following command to build the service images and start all containers. The `--build` flag is crucial for applying any code or dependency changes.

   ```bash
   docker compose up --build
   
   ```

   This command will start the `mssql` and `kafka` containers first, wait for them to become healthy, and then start the `notifications-service` and other services.

4. **Test the Service**: After the containers are running, send a payment request to the `bill-pay` service. You will see a `SIMULATED EMAIL` or `SIMULATED SMS` log message appear in the console output for the `notifications-servic